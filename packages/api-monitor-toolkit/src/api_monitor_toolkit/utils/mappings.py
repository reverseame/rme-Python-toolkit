from enum import Enum

class AttachMode(str, Enum):
    """
    Different methods to attach API Monitor to the target process.
    """
    STATIC_IMPORT = "static-import"
    CONTEXT_SWITCH = "context-switch"
    INTERNAL_DEBUGGER = "internal-debugger"
    REMOTE_THREAD_EXTENDED = "remote-thread-extended"
    REMOTE_THREAD_STANDARD = "remote-thread-standard"


SUMMARY_MAPPING = {
    "#": "id",
    "Date & Time": "timestamp",
    "Time of Day": "time",
    "Relative Time": "rel_time",
    "Thread": "thread",
    "TID": "tid",
    "Module": "module",
    "Category": "category",
    "API": "api",
    "Return Type": "return_type",
    "Return Value": "return_value",
    "Return Address": "return_address",
    "Error": "error",
    "Duration": "duration",
    "Full Category": "full_category",
}

PARAMS_MAPPING = {
    "#": "id",
    "Type": "type",
    "Name": "name",
    "Pre-Call Value": "before",
    "Post-Call Value": "after",
}

CALLSTACK_MAPPING = {
    "#": "id",
    "Module": "module",
    "Address": "address",
    "Offset": "offset",
    "Location": "location",
}