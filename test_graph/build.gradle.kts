plugins {
    id("com.hayden.testgraphsdk.graph")
}

validationGraph {
    sourcesDir("sources")

    testGraph("specWorkflow") {
        node("sources/tla_spec_dev_cli_install.py")
        node("sources/spec_workflow_create_repo.py")
        node("sources/spec_workflow_start_ticket.py")
        node("sources/spec_workflow_complete_ticket.py")
        node("sources/spec_workflow_spec_units.py")
        node("sources/spec_workflow_close_ticket.py")
        node("sources/spec_workflow_failure_cleanup_probe.py")
        node("sources/spec_workflow_cleanup.py")
        // G-12: the reference adapters must import where an adopter runs them,
        // asserted where the environment cannot supply the answer. Its unit
        // test was green for a property of the operator's machine.
        node("sources/reference_adapters_resolve.py")
    }

    testGraph("cliWorkflow") {
        node("sources/tla_spec_dev_cli_install.py")
        node("sources/tla_spec_dev_cli_help.py")
    }

    testGraph("effectProviderExamples") {
        node("sources/effect_provider_examples.py")
    }

    /*
     * SI-16: skt's graphs, merged in with the plugin-to-plugin migration.
     * They assert what an import cannot reach -- the install script, the
     * wrapper it writes, and the two shell hooks -- and after the demotion
     * those artifacts live at THIS plugin's root, so they now measure the
     * carrier layout rather than skt's former standalone one.
     */
    testGraph("sktSurface") {
        node("sources/skt_wrapper_installed.py")
        node("sources/skt_status_tiers.py")
        node("sources/skt_workflow_agents.py")
        node("sources/skt_check_cached.py")
        node("sources/skt_hook_contract.py")
        node("sources/skt_ticket_roundtrip.py")
    }

    // The subset a hook change reruns, and nothing else.
    testGraph("sktHooks") {
        node("sources/skt_wrapper_installed.py")
        node("sources/skt_check_cached.py")
        node("sources/skt_hook_contract.py")
    }
}
