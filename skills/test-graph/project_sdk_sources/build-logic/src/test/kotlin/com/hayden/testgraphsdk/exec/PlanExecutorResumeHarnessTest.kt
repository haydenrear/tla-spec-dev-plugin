package com.hayden.testgraphsdk.exec

import com.hayden.testgraphsdk.MiniJson
import com.hayden.testgraphsdk.NodeKind
import com.hayden.testgraphsdk.ValidationNodeSpec
import com.hayden.testgraphsdk.ValidationRuntime
import org.gradle.testfixtures.ProjectBuilder
import java.io.File
import java.nio.file.Files
import kotlin.test.Test
import kotlin.test.assertContains
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class PlanExecutorResumeHarnessTest {

    @Test
    fun readsSavedInputContextSnapshot() {
        val reportRoot = Files.createTempDirectory("test-graph-resume").toFile()
        val input = listOf(
            ContextItem("app.running", mapOf("ready" to "true")),
            ContextItem("user.seeded", mapOf("userId" to "demo-user")),
        )

        writeInputContextSnapshot(input, reportRoot, "login.smoke")

        assertEquals(input, readInputContextSnapshot(reportRoot, "login.smoke"))
    }

    @Test
    fun inputContextSnapshotsAreAtomicNoReplaceAndDoNotFollowSymlinks() {
        val reportRoot = Files.createTempDirectory("test-graph-immutable-context").toFile()
        val original = listOf(ContextItem("upstream", mapOf("value" to "original")))
        writeInputContextSnapshot(original, reportRoot, "selected")

        assertFailsWith<IllegalArgumentException> {
            writeInputContextSnapshot(
                listOf(ContextItem("upstream", mapOf("value" to "replacement"))),
                reportRoot,
                "selected",
            )
        }
        assertEquals(original, readInputContextSnapshot(reportRoot, "selected"))

        val linkedRoot = Files.createTempDirectory("test-graph-linked-context-target").toFile()
        val contextDir = linkedRoot.resolve("context").apply { mkdirs() }
        val external = Files.createTempFile("test-graph-external-context", ".json")
        Files.writeString(external, "external")
        Files.createSymbolicLink(contextDir.resolve("selected.input.json").toPath(), external)
        assertFailsWith<IllegalArgumentException> {
            writeInputContextSnapshot(emptyList(), linkedRoot, "selected")
        }
        assertEquals("external", Files.readString(external))
    }

    @Test
    fun publishedObjectRangeIgnoresBracesInsideStrings() {
        val envelope = """
            {"nodeId":"env","published":{"path":"literal } brace","escaped":"quote \" and }"},"status":"passed"}
        """.trimIndent()

        val range = jsonObjectValueRange(envelope, "\"published\"")
            ?: error("expected published object range")
        val updated = envelope.replaceRange(range, "\"published\":{\"EnvironmentId\":\"env-1\"}")

        assertEquals(
            """{"nodeId":"env","published":{"EnvironmentId":"env-1"},"status":"passed"}""",
            updated,
        )
    }

    @Test
    fun publishedObjectRangeFindsTopLevelKeyOutsideEarlierStrings() {
        val envelope = """
            {"nodeId":"env","log":"before \"published\": {\"bad\":\"}\"}","published":{"path":"ok"},"status":"passed"}
        """.trimIndent()

        val range = jsonObjectValueRange(envelope, "\"published\"")
            ?: error("expected published object range")
        val updated = envelope.replaceRange(range, "\"published\":{\"EnvironmentId\":\"env-1\"}")

        assertEquals(
            """{"nodeId":"env","log":"before \"published\": {\"bad\":\"}\"}","published":{"EnvironmentId":"env-1"},"status":"passed"}""",
            updated,
        )
    }

    @Test
    fun mergePublishedPreservesOnlyExactStringContextAndAddsEnvironmentOutputs() {
        val merged = PlanExecutor.mergePublished(
            """{"nodeId":"env","status":"passed","published":{"child":"value"}}""",
            linkedMapOf("environment" to "ready"),
        )

        val published = MiniJson.obj(MiniJson.parse(merged))["published"]
        assertEquals(
            linkedMapOf("child" to "value", "environment" to "ready"),
            MiniJson.stringMap(published),
        )
    }

    @Test
    fun mergePublishedRejectsNonStringPublishedValuesWithoutCoercion() {
        listOf("7", "true", "null", "[]", "{}")
            .forEach { invalidValue ->
                assertFailsWith<IllegalArgumentException>(
                    "published value $invalidValue must not be coerced with toString()"
                ) {
                    PlanExecutor.mergePublished(
                        """{"nodeId":"env","status":"passed","published":{"bad":$invalidValue}}""",
                        mapOf("environment" to "ready"),
                    )
                }
            }

        assertFailsWith<IllegalArgumentException> {
            PlanExecutor.mergePublished(
                """{"nodeId":"env","status":"passed","published":{"bad":7}}""",
                emptyMap(),
            )
        }
    }

    @Test
    fun ordinarySelectionRetainsTheFullPlan() {
        val plan = listOf(node("one"), node("two"), node("three"))

        val selection = PlanExecutor.selectExecutionPlan(plan, resumeFromBuild = null)

        assertEquals(null, selection.selectedNodeIndex)
        assertEquals(listOf("one", "two", "three"), selection.executionPlan.map { it.id })
    }

    @Test
    fun resumeSelectionStartsAtSelectedNodeAndContinuesDownstream() {
        val plan = listOf(node("one"), node("two"), node("three"))

        val selection = PlanExecutor.selectExecutionPlan(
            plan,
            PlanExecutor.ResumeFromBuild(
                buildDir = File("source-run"),
                nodeId = "two",
                mode = PlanExecutor.BuildReplayMode.RESUME_GRAPH,
            ),
        )

        assertEquals(1, selection.selectedNodeIndex)
        assertEquals(listOf("two", "three"), selection.executionPlan.map { it.id })
    }

    @Test
    fun resumeRejectsMissingDependencyContext() {
        assertResumeRejected(
            sourceExpectedNodeIds = listOf("dependency", "selected"),
            selectedContext = emptyList(),
            expectedMessage = "exact current plan prefix",
        )
    }

    @Test
    fun resumeRejectsAClosedSourceWhoseFullPlanDiffersFromTheCurrentGraph() {
        assertResumeRejected(
            sourceExpectedNodeIds = listOf("dependency", "selected", "stale.tail"),
            selectedContext = listOf(ContextItem("dependency", emptyMap())),
            expectedMessage = "source full-plan node sequence",
        )
    }

    private fun assertResumeRejected(
        sourceExpectedNodeIds: List<String>,
        selectedContext: List<ContextItem>,
        expectedMessage: String,
    ) {
        System.setProperty("otel.traces.exporter", "none")
        System.setProperty("otel.metrics.exporter", "none")
        System.setProperty("otel.logs.exporter", "none")
        val projectRoot = Files.createTempDirectory("test-graph-missing-resume-context").toFile()
        val project = ProjectBuilder.builder().withProjectDir(projectRoot).build()
        val source = projectRoot.resolve("source").apply { mkdirs() }
        writeInputContextSnapshot(selectedContext, source, "selected")
        val contextJson = ContextSerde.toJson(selectedContext)
        val replaySnapshot = ReplaySourceSnapshot.immutable(
            sourceBuild = source.canonicalFile,
            graphName = "resumeDependencyCoverage",
            selectedNodeId = "selected",
            sourceExpectedNodeIds = sourceExpectedNodeIds,
            traceId = "0123456789abcdef0123456789abcdef",
            carrierJson =
                """{"traceparent":"00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"}""",
            carrier = mapOf(
                "traceparent" to
                        "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
            ),
            selectedContextJson = contextJson,
            selectedContext = selectedContext,
            closureSha256 = "0".repeat(64),
            selectedContextSha256 = sha256Utf8(contextJson),
        )
        val target = projectRoot.resolve("target").apply { mkdirs() }
        val targetDirectory = project.layout.dir(project.provider { target }).get()
        val observability = GraphObservability.open(target, "resumeDependencyCoverage")
        val neverRun = object : ValidationExecutor {
            override val runtimeName: String = "uv"
            override fun execute(invocation: NodeInvocation): ExecutionOutcome =
                error("executor must not launch when saved dependencies are incomplete")
        }
        val failure = try {
            assertFailsWith<IllegalArgumentException> {
                PlanExecutor(
                    registry = ExecutorRegistry(mapOf("uv" to neverRun)),
                    projectDir = project.layout.projectDirectory,
                    reportDir = targetDirectory,
                    runId = "target",
                    logger = project.logger,
                    graphName = "resumeDependencyCoverage",
                    observability = observability,
                ).run(
                    listOf(
                        node("dependency"),
                        node("selected", dependsOn = listOf("dependency")),
                    ),
                    PlanExecutor.ResumeFromBuild(source, "selected"),
                    replaySnapshot,
                )
            }
        } finally {
            observability.finish("failed", timeoutMillis = 10)
        }

        assertContains(failure.message.orEmpty(), expectedMessage)
    }

    @Test
    fun resumeRejectsSelectedRerunDisabledNode() {
        val plan = listOf(node("enabled"), node("disabled", rerun = false))

        assertFailsWith<IllegalArgumentException> {
            PlanExecutor.selectExecutionPlan(
                plan,
                PlanExecutor.ResumeFromBuild(
                    buildDir = File("source-run"),
                    nodeId = "disabled",
                ),
            )
        }
    }

    @Test
    fun runOnlySelectionContainsOnlySelectedNodeWithoutDownstreamContinuation() {
        val plan = listOf(node("one"), node("two"), node("three"))

        val selection = PlanExecutor.selectExecutionPlan(
            plan,
            PlanExecutor.ResumeFromBuild(
                buildDir = File("source-run"),
                nodeId = "two",
                mode = PlanExecutor.BuildReplayMode.RUN_ONLY_NODE,
            ),
        )

        assertEquals(1, selection.selectedNodeIndex)
        assertEquals(listOf("two"), selection.executionPlan.map { it.id })
    }

    @Test
    fun nestedResumeRetainsFullPlanAndExecutesOnlyTheUnfinishedSuffix() {
        System.setProperty("otel.traces.exporter", "none")
        System.setProperty("otel.metrics.exporter", "none")
        System.setProperty("otel.logs.exporter", "none")
        val root = Files.createTempDirectory("test-graph-nested-resume").toFile()
        val project = ProjectBuilder.builder().withProjectDir(root).build()
        val graph = "nestedResume"
        val plan = listOf(node("one"), node("two", dependsOn = listOf("one")),
            node("three", dependsOn = listOf("two")))
        val launched = mutableListOf<String>()
        fun attempt(name: String, source: File? = null, selected: String? = null,
                    failAt: String? = null): File {
            val target = root.resolve(name).apply { mkdirs() }
            val snapshot = source?.let {
                com.hayden.testgraphsdk.tasks.RunReportWriter.requireReplaySource(it, graph, selected!!)
            }
            val replay = snapshot?.let {
                com.hayden.testgraphsdk.tasks.RunReportWriter.ReplayMetadata(
                    com.hayden.testgraphsdk.tasks.RunReportWriter.ReplayMode.RESUME_FROM_NODE,
                    selected!!, source!!, it.closureSha256, it.selectedContextSha256)
            }
            val ids = if (selected == null) plan.map { it.id }
                else plan.dropWhile { it.id != selected }.map { it.id }
            com.hayden.testgraphsdk.tasks.RunReportWriter.persistExecutionScope(target, graph, ids, replay)
            val obs = GraphObservability.open(target, graph, replaySourceSnapshot = snapshot)
            val executor = object : ValidationExecutor {
                override val runtimeName = "uv"
                override fun execute(invocation: NodeInvocation): ExecutionOutcome {
                    val id = invocation.spec.id
                    launched += id
                    val status = if (id == failAt) "failed" else "passed"
                    val now = java.time.Instant.now().toString()
                    invocation.resultOut.writeText("""{"nodeId":"$id","status":"$status","startedAt":"$now","endedAt":"$now","assertions":[],"artifacts":[],"processes":[],"metrics":{},"logs":[],"published":{"value":"$id"}}""")
                    return ExecutionOutcome.Completed(0)
                }
            }
            try {
                val run = {
                    PlanExecutor(ExecutorRegistry(mapOf("uv" to executor)),
                        project.layout.projectDirectory,
                        project.layout.dir(project.provider { target }).get(), name,
                        project.logger, graph, obs).run(plan,
                        source?.let { PlanExecutor.ResumeFromBuild(it, selected!!) }, snapshot)
                }
                if (failAt == null) run() else {
                    val failure = assertFailsWith<RuntimeException> { run() }
                    assertContains(failure.message.orEmpty(), "node $failAt failed")
                }
                com.hayden.testgraphsdk.tasks.RunReportWriter.persistAttemptClosure(
                    target, graph, ids, obs.traceId, replay)
            } finally { obs.finish(if (failAt == null) "passed" else "failed", timeoutMillis = 10) }
            return target
        }
        val full = attempt("full", failAt = "two")
        assertEquals(listOf("one", "two"), launched)
        launched.clear()
        val resumed = attempt("resumed", full, "two", failAt = "three")
        assertEquals(listOf("two", "three"), launched)
        val snapshot = com.hayden.testgraphsdk.tasks.RunReportWriter.requireReplaySource(resumed, graph, "three")
        assertEquals(listOf("one", "two", "three"), snapshot.sourceExpectedNodeIds)
        assertEquals(listOf("one", "two"), snapshot.selectedContext.map { it.nodeId })
        launched.clear()
        val nested = attempt("nested", resumed, "three", failAt = "three")
        assertEquals(listOf("three"), launched)
        launched.clear()
        attempt("next", nested, "three")
        assertEquals(listOf("three"), launched)
        // The ordinary full-plan mismatch control still exercises PlanExecutor's
        // unchanged guard; the nested loader must not shorten its effective plan.
        assertResumeRejected(listOf("dependency", "selected", "stale.tail"),
            listOf(ContextItem("dependency", emptyMap())), "source full-plan node sequence")
        val ancestorContext = full.resolve("context/two.input.json")
        ancestorContext.appendText(" ")
        assertFailsWith<IllegalArgumentException> {
            com.hayden.testgraphsdk.tasks.RunReportWriter.requireReplaySource(resumed, graph, "three")
        }
    }

    private fun node(
        id: String,
        rerun: Boolean = true,
        dependsOn: List<String> = emptyList(),
    ): ValidationNodeSpec = ValidationNodeSpec(
        id = id,
        kind = NodeKind.EVIDENCE,
        runtime = ValidationRuntime.Uv("$id.py"),
        dependsOn = dependsOn,
        tags = emptySet(),
        timeout = "30s",
        retries = 0,
        cacheable = false,
        sideEffects = emptySet(),
        inputs = emptyMap(),
        outputs = emptyMap(),
        rerun = rerun,
    )
}
