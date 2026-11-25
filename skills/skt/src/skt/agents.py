"""Plugin workflow roles. Each role owns its inputs, brief and result handling."""
import argparse

from . import regress


def run_regress(values, parser):
    args = parser.parse_intermixed_args(["run", *values])
    return regress.main(args)


# A role gets the tail of its command line, so its options and positional
# inputs have the same semantics as its direct entry point.
def add_parser(sub, regress_parser):
    roles = {"regress": lambda values: run_regress(values, regress_parser)}
    agent = sub.add_parser("agent", help="run a workflow role through meta-harness")
    verbs = agent.add_subparsers(dest="agent_verb", required=True)
    listing = verbs.add_parser("list", help="list available workflow roles")
    def list_roles(_args):
        print("\n".join(sorted(roles)))
        return 0
    listing.set_defaults(agent_command=list_roles)
    run = verbs.add_parser("run", help="dispatch one workflow role")
    run.add_argument("role", choices=sorted(roles))
    run.add_argument("inputs", nargs=argparse.REMAINDER)
    run.set_defaults(agent_command=lambda args: roles[args.role](args.inputs))
