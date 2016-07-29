import copy
import json
import sys
import enum

class Flags(enum.Enum):
    ELIDE_TYPE_NAMES = 0x1 # Indicates that obfuscated type
                           # names should be used in the RPC payload.
    RPC_TOKEN_INCLUDED = 0x2 # Indicates that RPC token is included
                             # in the RPC payload.

class Verbose(enum.Enum):
    default = 1
    silent = 2
    verbose = 3
    vverbose = 4

class GWTParse(object):
    def __init__(self):
        self.orig_str = None
        self.version = None
        self.flags = []
        self.url = None
        self.name = None
        self.gwt_class = None
        self.gwt_method = None
        self.parameters = []

    def __str__(self):
        return str(self.version) + " " + str(self.flags) + " " + \
               str(self.url) + " " + str(self.name) + " " + \
               str(self.gwt_class) + "." + str(self.gwt_method) + " " + \
               str([str(s) for s in self.parameters])

class Parameter(object):
    STRING_OBJECT = "java.lang.String"
    INTEGER_OBJECT = "java.lang.Integer"
    DOUBLE_OBJECT = "java.lang.Double"
    FLOAT_OBJECT = "java.lang.Float"
    BYTE_OBJECT = "java.lang.Byte"
    BOOLEAN_OBJECT = "java.lang.Boolean"
    SHORT_OBJECT = "java.lang.Short"
    CHAR_OBJECT = "java.lang.Char"
    LONG_OBJECT = "java.lang.Long"

    PRIMITIVES_WRAPPER = [STRING_OBJECT, INTEGER_OBJECT, DOUBLE_OBJECT,
                          FLOAT_OBJECT, BYTE_OBJECT, BOOLEAN_OBJECT,
                          SHORT_OBJECT, CHAR_OBJECT]

    LONG = "J"
    DOUBLE = "D"
    FLOAT = "F"
    INT = "I"
    BYTE = "B"
    SHORT = "S"
    BOOLEAN = "Z"
    CHAR = "C"

    PRIMITIVES = [INT, DOUBLE, FLOAT, BYTE, BOOLEAN, SHORT, CHAR]
    NUMERICS = [INT, CHAR, BYTE, SHORT, INTEGER_OBJECT,
                CHAR_OBJECT, BYTE_OBJECT, SHORT_OBJECT]

    ARRAYLIST = "java.util.ArrayList"
    LINKEDLIST = "java.util.LinkedList"
    VECTOR = "java.util.Vector"

    LISTS = [ARRAYLIST, LINKEDLIST, VECTOR]

    def __init__(self, gwt_type, value):
        self.gwt_type = gwt_type
        self.value = value

    def to_dict(self):
        if not isinstance(self.value, list):
            return {self.gwt_type: self.value}
        else:
            return {self.gwt_type: [p.to_dict() for p in self.value]}

def safe_int_cast(candidate, radix):
    try:
        return int(candidate, radix)
    except ValueError:
        return None

def query_string_table(string_table, index):
    idx = int(index) - 1
    return string_table[idx]

def parse_flags(flags):
    res = []
    for flag in Flags:
        if flags & flag.value != 0:
            res.append(flag)
    return res

def decode(string_table, data_segment):
    qst_lambda = lambda p: query_string_table(string_table, p)
    safe_base10_cast = lambda n: safe_int_cast(n, 10)
    data_segment = copy.deepcopy(data_segment)

    ret = []
    ret += map(qst_lambda, data_segment[:4])
    data_segment = data_segment[4:]

    param_count = int(data_segment.pop(0))
    ret = ret + [param_count] + map(qst_lambda, data_segment[:param_count])
    data_segment = data_segment[param_count:]

    while len(data_segment) > 0:
        cur_arg = data_segment.pop(0)
        maybe_value = safe_base10_cast(cur_arg)
        if maybe_value is None or maybe_value < 1 or maybe_value > len(string_table):
            ret.append(cur_arg)
        else:
            data_string = qst_lambda(cur_arg)
            maybe_type = data_string.split("/")[0]

            if maybe_type in [Parameter.BOOLEAN, Parameter.BOOLEAN_OBJECT]:
                ret.append(Parameter(maybe_type, data_segment.pop(0) == '0'))
            elif maybe_type in [Parameter.FLOAT, Parameter.DOUBLE,
                                Parameter.FLOAT_OBJECT,
                                Parameter.DOUBLE_OBJECT]:
                ret.append(Parameter(maybe_type, float(data_segment.pop(0))))
            elif maybe_type in Parameter.NUMERICS:
                ret.append(Parameter(maybe_type, int(data_segment.pop(0))))
            elif maybe_type in Parameter.LISTS:
                ret.append(maybe_type)
                ret.append(int(data_segment.pop(0)))
            else:
                ret.append(data_string)
    return ret

def get_top_parameters(string_table, object_tracker, data, gwt_type, verbosity):

    if gwt_type == Parameter.STRING_OBJECT:
        ret = Parameter(gwt_type, data.pop(0))
    elif gwt_type in Parameter.PRIMITIVES + Parameter.PRIMITIVES_WRAPPER:
        ret = data.pop(0)
    elif gwt_type in Parameter.LISTS:
        param_count = data.pop(1)
        ret = get_object_parameters(string_table, object_tracker, data,
                                    param_count, gwt_type, verbosity)
    else:
        if verbosity == Verbose.silent or gwt_type in object_tracker:
            param_count = object_tracker[gwt_type]
        else:
            param_count = int(raw_input("How many parameters does %s have?: " % gwt_type))
            object_tracker[gwt_type] = param_count
        ret = get_object_parameters(string_table, object_tracker, data,
                                    param_count, gwt_type, verbosity)

    return ret

def get_object_parameters(string_table, object_tracker, data, param_count, gwt_type, verbosity):
    ret = Parameter(data.pop(0).split("/")[0], [])

    if ret.gwt_type != gwt_type and verbosity != Verbose.silent:
        print "Just a heads up, we're assosiating %s with %s" % (ret.gwt_type, gwt_type)

    for _ in range(param_count):
        if isinstance(data[0], Parameter):
            ret.value.append(data.pop(0))
        elif data[0].split("/")[0] in Parameter.LISTS:
            sub_p_count = data.pop(1)
            ret.value.append(get_object_parameter(string_table, data, sub_p_count, gwt_type))
        else:
            object_type = data[0].split("/")[0]
            if verbosity == Verbose.silent:
                if object_type in object_tracker:
                    sub_p_count = object_tracker[object_type]
                    ret.value.append(get_object_parameters(string_table, object_tracker, data,
                                                           sub_p_count, object_type, verbosity))
                else:
                    ret.value.append(Parameter(Parameter.STRING_OBJECT, data.pop(0)))
            else:
                if verbosity == Verbose.default and '.' not in data[0]:
                    ret.value.append(Parameter(Parameter.STRING_OBJECT, data.pop(0)))
                elif verbosity != Verbose.vverbose and object_type in object_tracker:
                    sub_p_count = object_tracker[object_type]
                    ret.value.append(get_object_parameters(string_table, object_tracker, data,
                                                           sub_p_count, object_type, verbosity))
                elif raw_input("Is %s an object (ie not a string value)? (y/[n]): " % data[0]) != 'y':
                    ret.value.append(Parameter(Parameter.STRING_OBJECT, data.pop(0)))
                else:
                    sub_p_count = int(raw_input("How many parameters does %s have?: " % object_type))
                    object_tracker[object_type] = sub_p_count
                    ret.value.append(get_object_parameters(string_table, object_tracker, data,
                                                           sub_p_count, object_type, verbosity))

    return ret


def parse(parse_string, object_tracker, verbosity):
    '''Convert a GWT RPC string into a GWTParse object'''
    res = GWTParse()

    data = parse_string.split("|") # split up the string into parameters
    if data[-1] == '':
        data = data[:-1]

    # Parse version and flags
    res.version = int(data.pop(0))
    res.flags = parse_flags(int(data.pop(0)))

    # Setup string and data tables
    str_table_len = int(data.pop(0))
    str_table = data[:str_table_len]
    data = data[str_table_len:]

    strings_data = decode(str_table, data)

    res.url, res.name, res.gwt_class, res.gwt_method = strings_data[:4]
    strings_data = strings_data[4:]

    param_count = strings_data.pop(0)
    param_types = [p.split("/")[0] for p in strings_data[:param_count]]
    strings_data = strings_data[param_count:]

    for p_type in param_types:
        param = get_top_parameters(str_table, object_tracker, strings_data, p_type, verbosity)
        res.parameters.append(param)

    return res

def main(parse_string):
    print parse(parse_string, {}, Verbose.default)

    return 0

if __name__ == '__main__':
    main(sys.argv[1])
