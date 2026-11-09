package com.hayden.testgraphsdk

import java.io.File
import kotlin.io.path.createTempDirectory
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertTrue
import kotlin.test.fail

/**
 * Issue #195 (BS-10, #138 CDC-ISF-023-F02): a describe that fails is an
 * environment problem until proven otherwise, so the loader retries it with a
 * bounded backoff. A describe that still fails after every attempt reports as
 * `errored` (the run did not complete), never as a node `failed` verdict.
 *
 * The node "interpreter" here is a fake `uv` shell script, so the test drives
 * the real process path: a counter file decides whether this attempt exits 1
 * or writes the describe JSON.
 */
class NodeDescribeLoaderRetryTest {

    private fun fixture(failFirst: Int): Triple<File, File, ToolPaths> {
        val dir = createTempDirectory("describe-retry-").toFile()
        val node = File(dir, "flakyNode.py").apply { writeText("# describe fixture\n") }
        val counter = File(dir, "attempts")
        val fakeUv = File(dir, "fake-uv").apply {
            writeText(
                """
                |#!/bin/sh
                |n=${'$'}(cat "${counter.absolutePath}" 2>/dev/null || echo 0)
                |n=${'$'}((n + 1))
                |echo "${'$'}n" > "${counter.absolutePath}"
                |if [ "${'$'}n" -le $failFirst ]; then
                |  echo "simulated interpreter start failure" >&2
                |  exit 1
                |fi
                |for arg in "${'$'}@"; do
                |  case "${'$'}arg" in
                |    --describe-out=*) out="${'$'}{arg#--describe-out=}" ;;
                |  esac
                |done
                |printf '%s' '{"id":"flaky.node","kind":"testbed"}' > "${'$'}out"
                |""".trimMargin()
            )
            setExecutable(true)
        }
        return Triple(dir, node, ToolPaths(jbang = "/bin/false", uv = fakeUv.absolutePath))
    }

    private fun attempts(dir: File): Int = File(dir, "attempts").readText().trim().toInt()

    @Test
    fun describeThatFailsOnceThenSucceedsPasses() {
        val (dir, node, tools) = fixture(failFirst = 1)

        val spec = NodeDescribeLoader.describe(node, dir, tools)

        assertEquals("flaky.node", spec.id)
        assertEquals(2, attempts(dir), "the loader should have retried exactly once")
    }

    @Test
    fun describeThatAlwaysFailsReportsErroredNotFailed() {
        val (dir, node, tools) = fixture(failFirst = Int.MAX_VALUE)

        val error = try {
            NodeDescribeLoader.describe(node, dir, tools)
            fail("a describe that always fails must not produce a spec")
        } catch (e: IllegalStateException) {
            e
        }

        assertEquals(
            "NodeDescribeErroredException",
            error.javaClass.simpleName,
            "a persistent describe failure must be its own errored type, not a generic failure",
        )
        val message = error.message.orEmpty()
        assertTrue(message.startsWith("errored:"), "message must lead with the errored outcome: $message")
        assertTrue("not a node failure" in message, "message must separate errored from failed: $message")
        assertTrue(attempts(dir) > 1, "the loader must retry before reporting errored")
        assertEquals(3, attempts(dir), "the retry must be bounded")
    }
}
