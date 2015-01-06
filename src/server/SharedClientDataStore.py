import threading
from ClientAPI import BaseContext, expose

class SharedClientDataStore:
    class Context(BaseContext):
        def instance(self, global_context):
            return global_context.network.store

    LIST_FILTERS = {
        "len_lt": lambda l,v: len(l) < v,
        "len_gt": lambda l,v: len(l) > v,
        "len_le": lambda l,v: len(l) <= v,
        "len_ge": lambda l,v: len(l) >= v,
        "len_eq": lambda l,v: len(l) == v,

        "empty": lambda l,v: len(l) == 0,
    }

    SCALAR_FILTERS = {
        "lt": lambda x,v: x < v,
        "gt": lambda x,v: x > v,
        "le": lambda x,v: x <= v,
        "ge": lambda x,v: x >= v,
        "eq": lambda x,v: x == v
    }

    KEY_FILTERS = {
        "unset": lambda d,k,v: k not in d,
        "set": lambda d,k,v: k in d,
    }

    def __init__(self):
        self.__data = {}
        self.readonly = []
        self.lock = threading.Lock()

    def __get(self, key):
        return self.__data[key]

    def __val(self, val):
        try:
            if val.startswith("#"):
                if val[1:] in self.__data:
                    return self.__data[val[1:]]
                else:
                    return None
            elif val.startswith("\\#"):
                # They actually wanted to start it with a pound for some reason...
                return val[2:]
            else:
                return val
        except AttributeError:
            # val is not a string...
            return val

    def __handle_filters(self, key, filters, kinds=None):
        if filters:
            if not kinds:
                kinds = ["key", "scalar"]

            for f_name, f_val in filters.items():
                try:
                    if "scalar" in kinds and f_name in self.SCALAR_FILTERS:
                        if not self.SCALAR_FILTERS[f_name](self.__data[key], self.__val(f_val)):
                            return False
                    if "list" in kinds and f_name in self.LIST_FILTERS:
                        if not self.LIST_FILTERS[f_name](self.__data[key], self.__val(f_val)):
                            return False
                    if "key" in kinds and f_name in self.KEY_FILTERS:
                        if not self.KEY_FILTERS[f_name](self.__data, key, self.__val(f_val)):
                            return False
                    # Assume key is in self.__data because it
                    # really should be, parent should check
                except TypeError:
                    # We'll consider this to mean that we tried to
                    # compare invalid types, which we can just
                    # assume means it was an invalid match?
                    print("Warning: Incompatible types using filter '{}' on '{}'".format(
                        f_name, key))
                    return False
        return True

    @expose
    def get(self, key, default=None):
        with self.lock:
            if key in self.__data:
                return self.__data[key]
            else:
                return default

    @expose
    def get_or_set_default(self, key, default, ro=False):
        val = self.get(key, default)
        with self.lock:
            if key not in self.__data:
                self.__data[key] = val
                if ro:
                    self.readonly.append(key)
        return val

    @expose
    def set(self, key, value, ro=False, **filters):
        with self.lock:
            if not self.__handle_filters(key, filters, kinds=["key"]):
                return (False, self.__data[key] if key in self.__data else None)

            if key in self.__data:
                if key not in self.readonly and self.__handle_filters(key, filters, kinds=["scalar"]):
                    self.__data[key] = value
                    if ro:
                        self.readonly.append(key)
                    return (True, value)
            return (False, None)

    @expose
    def set_if_missing(self, key, value, ro=False):
        return self.set(key, value, ro, unset=True)

    @expose
    def list_append(self, key, value=None, values=None, **filters):
        with self.lock:
            if not self.__handle_filters(key, filters, kinds=["key"]):
                return (False, self.__data[key] if key in self.__data else None)

            if key not in self.__data:
                if value:
                    self.__data[key] = [value]
                elif values:
                    self.__data[key] = list(values)
                else:
                    self.__data[key] = []
                return (True, self.__data[key])
            else:
                if not self.__handle_filters(key, filters, kinds=["list"]):
                    return (False, self.__data[key])

                if key not in self.readonly:
                    try:
                        if value:
                            self.__data[key].append(value)
                        elif values:
                            self.__data[key].extend(values)
                        else:
                            pass
                        return (True, self.__data[key])
                    except TypeError:
                        return (False, self.__data[key])
                else:
                    return (False, self.__data[key])

    @expose
    def list_set(self, key, index, value, **filters):
        with self.lock:
            if not self.__handle_filters(key, filters, kinds=["key"]):
                return (False, None)
            if key in self.__data:
                if not self.__handle_filters(key, filters, kinds=["list"]):
                    return (False, self.__data[key][index] if index < len(self.__data[key]) else None)

                if key not in self.readonly:
                    if index == len(self.__data[key]):
                        # Shortcut for append because we're nice
                        self.__data[key].append(value)
                    elif index < len(self.__data[key]):
                        self.__data[key][index] = value
                    else:
                        return (False, None)
                    return (True, self.__data[key][index])
                else:
                    return (False, None)
            else:
                # Make the thing if it doesn't exist because we're so nice
                self.__data[key] = [value]
                return (True, self.__data[key][index])

    @expose
    def list_get(self, key, index, slice_index=False, default=None):
        """
        Returns elements from a list, or the default value if the
        list item was not found. Allows retrieving slices as well,
        with the slice_index parameter. If index is None and
        slice_index is set, it will be treated as a slice of the
        form spam[:slice_index]. If index is given and slice_index
        is given, it will be treated as a slice of the form
        eggs[index:slice_index]. If index is given and slice_index
        is explicitly set to None, it will be treated as ham[index:]
        If slice_index is not given and index is, it will be treated
        as simple indexing. Indices out of range will result in the
        default value.
        """
        with self.lock:
            if key in self.__data:
                if index != None and slice_index is False:
                    try:
                        return self.__data[key][index]
                    except IndexError:
                        return default
                elif slice_index != False:
                    if index is None:
                        index = 0
                    return self.__data[key][index:slice_index]
                elif index != None and slice_index is None:
                    return self.data[key][index:]
            else:
                return None
