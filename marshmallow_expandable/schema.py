import logging

from marshmallow import fields


logger = logging.getLogger(__name__)


class ExpandableSchemaMixin(object):
    def __init__(self, extra=None, only=None, exclude=(), prefix='', strict=None,
                 many=False, context=None, load_only=(), dump_only=(),
                 partial=False, expand=()):
        super().__init__(extra, only, exclude, prefix, strict, many, context, load_only,
                         dump_only, partial)

        self._expand = self._normalize_expand(expand)

    def _normalize_expand(self, expand):
        """
        This function takes the list of fields to expand and assigns this attribute
        recursively, while assigning to self.expand the fields he is immediately interested
        """
        if expand is not None:
            self._BaseSchema__apply_nested_option('expand', expand, 'intersection')

            expand = self.set_class([field.split('.', 1)[0] for field in expand])

        return expand

    @property
    def expand(self):
        return self._expand

    @expand.setter
    def expand(self, value):
        """Every time we assign a new expand terms we need to normalize them"""
        self._expand = self._normalize_expand(value)


class ExpandableNested(fields.Nested):
    def __init__(self, nested, **kwargs):
        super().__init__(nested, **kwargs)
        self.expand = kwargs.get('expand', ())

    @property
    def schema(self):
        if self._Nested__schema:
            return self._Nested__schema

        schema = super().schema
        if isinstance(schema, ExpandableSchemaMixin):
            setattr(schema, 'expand', self.expand)

        return schema

    def _split_argument_map(self, argument):
        return argument if isinstance(argument, tuple) else (argument, argument)

    def _get_query_function_and_arguments(self, function_name):
        if not hasattr(self.schema.Meta, function_name):
            return None, None

        try:
            function, arguments = getattr(self.schema.Meta, function_name)
        except Exception as e:
            raise Exception('The interactor Meta attribute should be a tuple composed '
                            'by the function to build the interactor and the list of parameters') from e

        argument_map = dict(self._split_argument_map(arg) for arg in arguments)
        """Maps a queryparam from the schema to the interactor"""

        return function, argument_map

    def _get_query_functions(self):
        retrieve_func, retrieve_argument_map = self._get_query_function_and_arguments('retrieve')
        batch_func, batch_arguments_map = self._get_query_function_and_arguments('batch')

        return retrieve_func, retrieve_argument_map, batch_func, batch_arguments_map

    def _serialize(self, nested_obj, attr, obj):
        should_expand = hasattr(self.root, 'expand') and attr in self.root.expand
        resource = self._expand_resource(nested_obj) if should_expand else nested_obj
        return super()._serialize(resource, attr, obj)

    def _expand_resource(self, nested_obj):
        retrieve_func, argument_map, batch_func, batch_argument_map = self._get_query_functions()
        can_use_batch_function = self.many and batch_func is not None

        if can_use_batch_function:
            arguments = self._generate_batch_arguments(nested_obj, batch_argument_map)
            result = self._execute_query(batch_func, arguments)
        elif self.many:
            arguments = [{argument: o[attribute_in_schema] for argument, attribute_in_schema in argument_map.items()} for o in nested_obj]
            result = [self._execute_query(retrieve_func, qparam) for qparam in arguments]
        else:
            arguments = {argument: nested_obj[attribute_in_schema] for argument, attribute_in_schema in argument_map.items()}
            result = self._execute_query(retrieve_func, arguments)

        return result

    def _execute_query(self, retrieve_func, arguments):
        resource_or_interactor = retrieve_func(**arguments)
        is_interactor = hasattr(resource_or_interactor, 'execute')
        return resource_or_interactor.execute if is_interactor else resource_or_interactor

    def _generate_batch_arguments(self, obj, argument_map):
        assert self._is_iterable(obj), 'The object is not a list as expected!'
        return {argument: [o[attribute_in_schema] for o in obj] for argument, attribute_in_schema in argument_map.items()}

    def _is_iterable(self, obj):
        try:
            iter(obj)
            return True
        except TypeError:
            return False


