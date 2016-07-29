import argparse
import json

import parse_gwt as parseGWT

def main():
    Verbose = parseGWT.Verbose
    parser = argparse.ArgumentParser(description = "Parse GWT RPC Calls")

    parser.add_argument("rpc_string", help = "The GWT string")
    parser.add_argument("-c", "--classes", help = "A JSON object of classes", type=json.loads)
    parser.add_argument("-s", help = "Parse in silent mode", action="store_true")
    parser.add_argument("-v", help = "Parse in verbose mode", action="store_true")
    parser.add_argument("-vv", help = "Parse in very verbose mode", action="store_true")

    args = parser.parse_args()

    if args.s:
        verbosity = Verbose.silent
    elif args.v:
        verbosity = Verbose.verbose
    elif args.vv:
        verbosity = Verbose.vverbose
    else:
        verbosity = Verbose.default

    classes = {}
    if args.classes:
        classes = args.classes

    res = parseGWT.parse(args.rpc_string, classes, verbosity)

    pp_string = '''\
Version: %s
Flags: %s
URL: %s
Name: %s
Method: %s.%s
Parameters:\
''' % (res.version, res.flags, res.url, res.name, res.gwt_class, res.gwt_method)

    for param in res.parameters:
        pp_string += json.dumps(param.to_dict(), sort_keys=True, indent=4, separators=(',', ': '))
    print pp_string

    return 0


if __name__ == '__main__':
    main()
