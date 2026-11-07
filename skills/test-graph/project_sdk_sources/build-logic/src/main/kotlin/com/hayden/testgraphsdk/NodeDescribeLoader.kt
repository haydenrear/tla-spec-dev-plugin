package com.hayden.testgraphsdk

import com.hayden.testgraphsdk.exec.ExecutionOutcome
import com.hayden.testgraphsdk.exec.PosixProcessGroupController
import com.hayden.testgraphsdk.exec.awaitWithTimeout
import java.io.File

/**
 * Node discovery by self-describe.
 *
 * Every script the plugin cares about is invoked with
 * `--describe-out=<tmp>`; the SDK writes its spec JSON to <tmp> and exits
 * without running the body. We parse that JSON into a ValidationNodeSpec.
 *
 * Runtime is inferred from the file extension:
 *   .java → jbang     .py → uv
 */
internal object NodeDescribeLoader {

    /**
     * Describe one script file using the given resolved tool paths.
     *
     * A describe that exits non-zero, times out, breaks the process contract or
     * writes no output is retried up to [DESCRIBE_ATTEMPTS] times with an
     * exponential backoff: a flaky interpreter start is an environment problem,
     * not a red node (#195, REG-010). When every attempt fails the loader throws
     * [NodeDescribeErroredException] — the `errored` outcome (#175: the run did
     * not complete) — never a node `failed` verdict. Malformed describe JSON is
     * deterministic and is not retried.
     */
    fun describe(file: File, projectDir: File, tools: ToolPaths): ValidationNodeSpec {
        require(file.isFile) { "node script not found: ${file.path}" }
        val runtime = runtimeFor(file, projectDir)
        val argv = invocationFor(runtime, file, tools)
        val failures = mutableListOf<String>()
        for (attempt in 1..DESCRIBE_ATTEMPTS) {
            when (val result = describeOnce(file, projectDir, argv)) {
                is AttemptResult.Described -> return parseSpec(result.json, runtime, projectDir)
                is AttemptResult.Failed -> failures += "attempt $attempt: ${result.reason}"
            }
            if (attempt < DESCRIBE_ATTEMPTS) {
                Thread.sleep(DESCRIBE_BACKOFF_MILLIS shl (attempt - 1))
            }
        }
        throw NodeDescribeErroredException(
            "errored: describe for ${file.name} failed on all $DESCRIBE_ATTEMPTS attempts; " +
                "the run did not complete, which is not a node failure " +
                "(retry it or fix the environment). " +
                failures.joinToString("; ") +
                ". Run directly to debug: ${(argv + "--describe-out=<tmp>").joinToString(" ")}"
        )
    }

    private sealed interface AttemptResult {
        data class Described(val json: String) : AttemptResult
        data class Failed(val reason: String) : AttemptResult
    }

    private fun describeOnce(file: File, projectDir: File, baseArgv: List<String>): AttemptResult {
        val out = File.createTempFile("validation-describe-", ".json").apply { deleteOnExit() }
        try {
            val argv = baseArgv + "--describe-out=${out.absolutePath}"
            val managedCommand = PosixProcessGroupController.wrap(argv)
            val process = try {
                ProcessBuilder(managedCommand.arguments)
                    .directory(projectDir)
                    .redirectErrorStream(true)
                    .redirectOutput(ProcessBuilder.Redirect.DISCARD)
                    .start()
            } catch (e: java.io.IOException) {
                return AttemptResult.Failed("could not start describe process: ${e.message}")
            }
            val outcome = awaitWithTimeout(process, DESCRIBE_TIMEOUT_MILLIS, managedCommand)
            val code = when (outcome) {
                is ExecutionOutcome.Completed -> outcome.exitCode
                is ExecutionOutcome.ProcessContractViolation ->
                    return AttemptResult.Failed("process contract failed: ${outcome.reason}")
                ExecutionOutcome.TimedOut ->
                    return AttemptResult.Failed("timed out after ${DESCRIBE_TIMEOUT_MILLIS}ms")
            }
            if (code != 0) return AttemptResult.Failed("exit=$code")
            if (!out.isFile || out.length() == 0L) {
                return AttemptResult.Failed(
                    "no describe output (did the script call Node.run(args, spec, body)?)"
                )
            }
            return AttemptResult.Described(out.readText())
        } finally {
            out.delete()
        }
    }

    /**
     * Describe every .java / .py script under a directory.
     * Returns a map keyed by the spec id.
     */
    fun indexDir(dir: File, projectDir: File, tools: ToolPaths): Map<String, ValidationNodeSpec> {
        require(dir.isDirectory) { "sources dir not found: ${dir.path}" }
        val out = linkedMapOf<String, ValidationNodeSpec>()
        dir.listFiles { f -> f.isFile && f.extension in setOf("java", "py") }
            ?.sortedBy { it.name }
            ?.forEach { file ->
                val spec = describe(file, projectDir, tools)
                if (out.containsKey(spec.id)) {
                    error("duplicate node id '${spec.id}' in ${dir.path} " +
                            "(second source: ${file.name})")
                }
                out[spec.id] = spec
            }
        return out
    }

    private fun runtimeFor(file: File, projectDir: File): ValidationRuntime {
        val rel = file.relativeTo(projectDir).path.replace(File.separatorChar, '/')
        return when (file.extension) {
            "java" -> ValidationRuntime.JBang(rel)
            "py"   -> ValidationRuntime.Uv(rel)
            else   -> error("no runtime for file extension '.${file.extension}' (${file.path})")
        }
    }

    private fun invocationFor(runtime: ValidationRuntime, file: File, tools: ToolPaths): List<String> =
        when (runtime) {
            is ValidationRuntime.JBang -> listOf(tools.jbang, file.absolutePath)
            is ValidationRuntime.Uv    -> listOf(tools.uv, "run", file.absolutePath)
        }

    private fun parseSpec(json: String, runtime: ValidationRuntime, projectDir: File): ValidationNodeSpec {
        val root = MiniJson.obj(MiniJson.parse(json))
        val id = MiniJson.str(root["id"]) ?: error("describe output missing id")
        val kind = NodeKind.valueOf((MiniJson.str(root["kind"]) ?: "action").uppercase())
        val reports = MiniJson.obj(root["reports"] ?: emptyMap<String, Any?>())
        val sideEffects = MiniJson.stringList(root["sideEffects"]).toSet()
        SideEffectSpec.parseAll(sideEffects, "node '$id' sideEffects")
        return ValidationNodeSpec(
            id = id,
            kind = kind,
            runtime = runtime,
            dependsOn = MiniJson.stringList(root["dependsOn"]),
            tags = MiniJson.stringList(root["tags"]).toSet(),
            timeout = MiniJson.str(root["timeout"]) ?: "60s",
            retries = (root["retries"] as? Long)?.toInt()?.coerceAtLeast(0) ?: 0,
            rerun = (root["rerun"] as? Boolean) ?: true,
            cacheable = MiniJson.bool(root["cacheable"]),
            sideEffects = sideEffects,
            environmentRepository = EnvironmentRepositorySpec.parse(
                root["environmentRepository"],
                "node '$id' environmentRepository",
                projectDir,
            ),
            inputs = MiniJson.stringMap(root["inputs"]),
            outputs = MiniJson.stringMap(root["outputs"]),
            reports = ReportsSpec(
                structuredJson = (reports["structuredJson"] as? Boolean) ?: true,
                junitXml = MiniJson.bool(reports["junitXml"]),
                cucumber = MiniJson.bool(reports["cucumber"]),
            ),
        )
    }

    private const val DESCRIBE_TIMEOUT_MILLIS = 2 * 60 * 1000L
    private const val DESCRIBE_ATTEMPTS = 3
    private const val DESCRIBE_BACKOFF_MILLIS = 250L
}

/**
 * A describe that failed on every bounded retry. Its outcome is `errored` (the
 * run did not complete: environment, interpreter start, timeout), distinct from
 * a node that ran and went red (`failed`). Subclasses [IllegalStateException]
 * so callers that caught the old `error(...)` keep working.
 */
class NodeDescribeErroredException(message: String) : IllegalStateException(message) {
    val outcome: String get() = "errored"
}
