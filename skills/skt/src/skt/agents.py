"""Plugin workflow roles. Each role owns its inputs, brief and result handling."""
import argparse

from . import regress, review


def review_command(values, _regress_parser):
    return review.run(values)


def regress_command(values, regress_parser):
    args = regress_parser.parse_intermixed_args(["run", *values])
    return regress.main(args)


# Keep role-specific flags with their role; graph flags retain the same
# intermixing behavior as the existing regress parser.
ROLE_COMMANDS = {"regress": regress_command, "review": review_command}


def list_roles(_args):
    print("\n".join(sorted(ROLE_COMMANDS)))
    return 0


def add_parser(sub, regress_parser):
    agent = sub.add_parser("agent", help="run a workflow role through meta-harness")
    verbs = agent.add_subparsers(dest="agent_verb", required=True)
    listing = verbs.add_parser("list", help="list available workflow roles")
    listing.set_defaults(agent_command=list_roles)
    run = verbs.add_parser("run", help="dispatch one workflow role")
    run.add_argument("role", choices=sorted(ROLE_COMMANDS))
    run.add_argument("inputs", nargs=argparse.REMAINDER)
    run.set_defaults(agent_command=lambda args: ROLE_COMMANDS[args.role](args.inputs, regress_parser))
