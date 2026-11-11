package com.hayden.testgraphsdk.sdk;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
class NodeResultVerdictsTest {
    @Test void emptyAssertionCannotBecomeTerminalGreen() {
        var result=NodeResult.pass("fixture");
        assertEquals(NodeStatus.PASSED,result.status());
        result.requireAssertionObservation(NodeSpec.of("fixture").kind(NodeSpec.Kind.ASSERTION));
        assertEquals(NodeStatus.FAILED,result.status());
    }
    @Test void observedAssertionAndFailureRemainTheirActualStatus() {
        var spec=NodeSpec.of("fixture").kind(NodeSpec.Kind.ASSERTION);
        assertEquals(NodeStatus.PASSED,NodeResult.pass("fixture").assertion("observed",true).requireAssertionObservation(spec).status());
        assertEquals(NodeStatus.FAILED,NodeResult.fail("fixture","actual failure").requireAssertionObservation(spec).status());
        assertEquals(NodeStatus.ERRORED,NodeResult.error("fixture",new IllegalStateException("unavailable")).requireAssertionObservation(spec).status());
    }
}
