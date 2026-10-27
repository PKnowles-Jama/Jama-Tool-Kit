import argparse
from pathlib import Path
from .jama_rest import Jama, connection_arguments
from .publisher import prepare, validate_package, publish


def main():
    parser = argparse.ArgumentParser(description='Jama Hardware Model Viewer')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare', help='Package exported artifacts after summary publication')
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--model', type=Path, required=True, action='append', help='Repeat for multiple models')
    for option in ('source', 'gif', 'drawing', 'document'):
        p.add_argument('--' + option, type=Path, action='append', default=[])
    p.add_argument('--revision', required=True)
    p.add_argument('--units', choices=['mm', 'cm', 'm', 'in', 'ft'], required=True)
    p.add_argument('--up-axis', choices=['Y', 'Z'], required=True)
    p.add_argument('--projection', choices=['first-angle', 'third-angle'], default='third-angle')
    p.add_argument('--drawing-kind', choices=['cad-drawing', 'undimensioned-visualization'], default='cad-drawing')
    p = sub.add_parser('validate')
    p.add_argument('--run', type=Path, required=True)
    p = sub.add_parser('draw', help='Generate a labeled undimensioned four-view PNG from GLB')
    p.add_argument('--model', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--up-axis', choices=['Y', 'Z'], default='Y')
    p.add_argument('--projection', choices=['first-angle', 'third-angle'], default='third-angle')
    p = sub.add_parser('publish')
    p.add_argument('--run', type=Path, required=True)
    connection_arguments(p)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--preflight', action='store_true')
    mode.add_argument('--apply', action='store_true')
    p = sub.add_parser('serve')
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8090)
    p.add_argument('--demo', action='store_true', help='Expose synthetic fixture for local qualification')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args)
    elif args.command == 'validate':
        validate_package(args.run.resolve())
        print('Package valid; no Jama writes made.')
    elif args.command == 'draw':
        from .drawing import illustrate
        illustrate(args.model, args.output, args.up_axis, args.projection)
        print('Generated undimensioned four-view illustration; not a CAD engineering drawing.')
    elif args.command == 'publish':
        # Validate before authenticating, so malformed input makes no network calls.
        validate_package(args.run.resolve())
        lock = args.run / 'viewer-publish.lock'
        try:
            lock.open('x').close()
        except FileExistsError:
            raise ValueError('Publisher is already running, or a stale lock needs reconciliation') from None
        try:
            publish(args, Jama(args))
        finally:
            lock.unlink()
    else:
        from .server import serve
        serve(args)
