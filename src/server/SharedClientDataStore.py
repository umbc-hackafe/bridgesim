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
        "contains": lambda l,v: v in l,
        "not_contains": lambda l,v: v not in l,

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

    def __init__(self, server):
        self.__data = {}
        self.readonly = []
        self.__updates = {}
        self.__clients = set()
        self.server = server
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

    def get_updates(self, client):
        if client.id not in self.__updates:
            return []
        return [{key: self.__data[key]} for key in self.__updates[client.id]]

    def queue_updates(self, key, caller):
        """
        Should be called on a set method, indicating that caller has updated
        key and all the other clients should have its new value queued. We
        assume that the given client will get the value and is thus already
        updated.
        """
        for client in self.__clients:
            if client != caller.id:
                if caller not in self.__updates:
                    self.__updates[caller.id] = set()
                self.__updates[client].add(key)

    def dequeue_update(self, key, caller):
        """
        This should be called on a get method, indicating that the client
        is up-to-date for this particular key. If the key is None, the client
        is to be considered up-to-date for all keys.
        """
        if caller.id not in self.__updates:
            self.__updates[caller.id] = set()
        if caller.id not in self.__clients:
            self.__clients.add(caller.id)

        if key is None:
            # do all of them
            self.__updates[caller.id] = set()
        else:
            self.__updates[caller.id].remove(key)

    @expose(client=True)
    def get(self, key, default=None, client=None):
        with self.lock:
            if key in self.__data:
                self.dequeue_update(key, client)
                return self.__data[key]
            else:
                return default

    @expose(client=True)
    def get_or_set_default(self, key, default, ro=False, client=None):
        val = self.get(key, default)
        with self.lock:
            if key not in self.__data:
                self.queue_updates(key, client)
                self.__data[key] = val
                if ro:
                    self.readonly.append(key)
        self.dequeue_update(key, client)
        return val

    @expose(client=True)
    def set(self, key, value, ro=False, client=None, **filters):
        with self.lock:
            if not self.__handle_filters(key, filters, kinds=["key"]):
                return (False, self.__data[key] if key in self.__data else None)

            if key in self.__data:
                if key not in self.readonly and self.__handle_filters(key, filters, kinds=["scalar"]):
                    self.__data[key] = value
                    self.queue_updates(key, client)
                    if ro:
                        self.readonly.append(key)
                    return (True, value)
            return (False, None)

    @expose(client=True)
    def set_if_missing(self, key, value, ro=False, client=None):
        return self.set(key, value, ro, unset=True, client=client)

    @expose(client=True)
    def list_append(self, key, value=None, values=None, client=None, **filters):
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
                self.queue_updates(key, client)
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
                        self.queue_updates(key, client)
                        return (True, self.__data[key])
                    except TypeError:
                        return (False, self.__data[key])
                else:
                    return (False, self.__data[key])

    @expose(client=True)
    def list_set(self, key, index, value, client=None, **filters):
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
                    self.queue_updates(key, client)
                    return (True, self.__data[key][index])
                else:
                    return (False, None)
            else:
                # Make the thing if it doesn't exist because we're so nice
                self.__data[key] = [value]
                self.queue_updates(key, client)
                return (True, self.__data[key][index])

    @expose(client=True)
    def list_get(self, key, index, slice_index=False, default=None, client=None):
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
                    self.dequeue_update(key, client)
                    return self.__data[key][index:slice_index]
                elif index != None and slice_index is None:
                    self.dequeue_update(key, client)
                    return self.data[key][index:]
            else:
                return None

    @expose(client=True)
    def delete(self, key, client=None, **filters):
        with self.lock:
            if not self.__handle_filters(key, filters, kinds=["key"]):
                return False

            if key in self.__data:
                if not self.__handle_filters(key, filters, kinds=["list"]):
                    return False
                del self.__data[key]
                self.queue_updates(key, client)
                return True
            else:
                return None

    @expose(client=True)
    def list_delete(self, key, index=None, end=None, value=None, client=None, **filters):
        # Check they aren't confusing us with parameters
        if (end and not index) or (value and (index or end)) or not (index or end or value):
            return False

        with self.lock:
            if not self.__handle_filters(key, filters, kinds=["key"]):
                return False
            if key in self.__data:
                if value != None:
                    try:
                        index = self.__data[key].index(value)
                    except ValueError:
                        return False

                if index >= len(self.__data[key]) or \
                   not self.__handle_filters(key, filters, kinds=["list"]):
                    return False

                if end:
                    del self.__data[key][index:end]
                else:
                    del self.__data[key][index]
                self.queue_updates(key, client)
                return self.__data[key]
            else:
                return None
