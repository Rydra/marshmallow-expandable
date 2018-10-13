class ArgumentBuilder:
    def build_arguments(self, resource, argument_map, aggregate=False, many=False):
        """
        Constructs the arguments to be passed to another function as kwargs from values in the resource.
        The aggregate is only applicable when many=True. Tells whether all the values from the
        resource should be aggregated into single variables
        """
        if not many:
            return {argument: resource[attribute_in_schema] for attribute_in_schema, argument in argument_map.items()}

        assert self._is_iterable(resource), 'The object is not iterable as expected!'

        if aggregate:
            return {argument: [o[attribute_in_schema] for o in resource] for attribute_in_schema, argument in argument_map.items()}

        return (
            [{argument: o[attribute_in_schema] for attribute_in_schema, argument in argument_map.items()}
             for o in resource]
        )

    def _is_iterable(self, obj):
        try:
            iter(obj)
            return True
        except TypeError:
            return False
