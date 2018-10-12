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

    def _get_interactor_and_params(self):
        if not hasattr(self.schema.Meta, 'retrieve'):
            raise Exception('The nested class does not have an "query_function" Meta '
                            'attribute, therefore it does not support expansion')

        try:
            retrieve_func, retrieve_arguments = self.schema.Meta.retrieve
        except Exception as e:
            raise Exception('The interactor Meta attribute should be a tuple composed '
                            'by the function to build the interactor and the list of parameters') from e

        try:
            batch_func, batch_arguments = self.schema.Meta.batch
        except Exception:
            batch_func, batch_arguments = None, None

        retrieve_argument_map = {}
        """Maps a queryparam from the schema to the interactor"""

        for arg in retrieve_arguments:
            if isinstance(arg, tuple):
                arg_in_interactor, arg_in_schema = arg
                retrieve_argument_map[arg_in_interactor] = arg_in_schema
            else:
                retrieve_argument_map[arg] = arg

        batch_argument_map = {}
        if batch_func:
            for arg in batch_arguments:
                arg_in_interactor, arg_in_schema = arg
                batch_argument_map[arg_in_interactor] = arg_in_schema

        return retrieve_func, retrieve_argument_map, batch_func, batch_argument_map

    def _serialize(self, nested_obj, attr, obj):
        resource = nested_obj

        if self._should_expand(attr):
            retrieve_func, argument_map, batch_func, batch_argument_map = self._get_interactor_and_params()

            if self.many and batch_func:
                arguments = self._generate_batch_arguments(nested_obj, batch_argument_map)
                result = self._execute_query(batch_func, arguments)
            else:
                arguments = self._generate_arguments(nested_obj, argument_map)

                if self.many:
                    result = [self._execute_query(retrieve_func, qparam) for qparam in arguments]
                else:
                    result = self._execute_query(retrieve_func, arguments)

            resource = result

        return super()._serialize(resource, attr, obj)

    def _execute_query(self, retrieve_func, qparams):
        resource_or_interactor = retrieve_func(**qparams)

        if self._is_interactor(resource_or_interactor):
            result = resource_or_interactor.execute()
        else:
            result = resource_or_interactor

        return result

    def _is_interactor(self, resource_or_interactor):
        return hasattr(resource_or_interactor, 'execute')

    def _generate_batch_arguments(self, obj, argument_map):
        assert self._is_iterable(obj), 'The object is not a list as expected!'
        return {argument: [o[attribute_in_schema] for o in obj] for argument, attribute_in_schema in argument_map.items()}

    def _generate_arguments(self, obj, argument_map):
        if self.many:
            return [{argument: o[attribute_in_schema] for argument, attribute_in_schema in argument_map.items()} for o in obj]
        else:
            return {argument: obj[attribute_in_schema] for argument, attribute_in_schema in argument_map.items()}

    def _is_iterable(self, obj):
        try:
            iter(obj)
            return True
        except TypeError:
            return False

    def _should_expand(self, attr):
        # The only one that knows if we should expand this attribute or not is the root schema
        return hasattr(self.root, 'expand') and attr in self.root.expand
