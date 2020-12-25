
class ObjectView(object):
    """Object view of a dict, updating the passed in dict when values are set
    or deleted. "ObjectView" the contents of a dict...: """

    def __init__(self, d):
        # since __setattr__ is overridden, self.__dict = d doesn't work
        object.__setattr__(self, '_ObjectView__dict', d)

    # Dictionary-like access / updates
    def __getitem__(self, name):
        value = self.__dict[name]
        if isinstance(value, dict):  # recursively view sub-dicts as objects
            value = ObjectView(value)
        elif isinstance(value, (list, tuple, set)):
            value = []
            for i in self.__dict[name]:
                if isinstance(i, dict):
                    value.append(ObjectView(i))
                else:
                    value.append(i)

        return value

    def __iter__(self):
        return iter(self._ObjectView__dict)

    def __setitem__(self, name, value):
        self.__dict[name] = value

    def __delitem__(self, name):
        del self.__dict[name]

    # Object-like access / updates
    def __getattr__(self, name):
        return self[name] if name in self else None

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        del self[name]

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.__dict)

    def __str__(self):
        return str(self.__dict)

