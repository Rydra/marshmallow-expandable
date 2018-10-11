from marshmallow import fields


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
        if not hasattr(self.schema.Meta, 'query_function'):
            raise Exception('The nested class does not have an "query_function" Meta '
                            'attribute, therefore it does not support expansion')

        try:
            query_function_method, parameters = self.schema.Meta.query_function
        except Exception as e:
            raise Exception('The interactor Meta attribute should be a tuple composed '
                            'by the function to build the interactor and the list of parameters') from e

        query_param_map = {}
        """Maps a queryparam from the schema to the interactor"""

        for param in parameters:
            if isinstance(param, tuple):
                param_in_interactor, param_in_schema = param
                query_param_map[param_in_interactor] = param_in_schema
            else:
                query_param_map[param] = param

        return query_function_method, query_param_map

    def _serialize(self, nested_obj, attr, obj):
        resource = nested_obj
        if self._should_expand(attr):
            query_function_method, query_param_map = self._get_interactor_and_params()
            qparams = self._get_search_parameters(nested_obj, query_param_map)
            resource_or_interactor = query_function_method(**qparams)

            if self._is_interactor(resource_or_interactor):
                resource_or_interactor = resource_or_interactor.execute()

            resource = resource_or_interactor

        return super()._serialize(resource, attr, obj)

    def _is_interactor(self, resource_or_interactor):
        return hasattr(resource_or_interactor, 'execute')

    def _get_search_parameters(self, obj, params):
        return {query_param: obj[attr] for query_param, attr in params.items()}

    def _should_expand(self, attr):
        # The only one that knows if we should expand this attribute or not is the root schema
        return hasattr(self.root, 'expand') and attr in self.root.expand
