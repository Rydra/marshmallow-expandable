from marshmallow import Schema, fields

from marshmallow_expandable import ExpandableSchemaMixin
from marshmallow_expandable.schema import ExpandableNested, ArgumentBuilder


def get_my_nested_schema(id):
    return dict(id=id, attr3=f'pine-{id}', attr4=f'pineapple-{id}', attr7={'id': 7})


def get_my_nested_schema_batch(ids):
    return [get_my_nested_schema(i) for i in ids]


def get_another_nested_schema(my_id):
    return dict(id=my_id, attr5=f'apple-{my_id}',
                attr6=[{'id': get_my_nested_schema(i)['id']} for i in range(1, 3)])


class AnotherNestedSchema(ExpandableSchemaMixin, Schema):
    id = fields.Int()
    attr5 = fields.Str()
    attr6 = ExpandableNested('MyNestedSchema', many=True)

    class Meta:
        retrieve = get_another_nested_schema, [('id', 'my_id')]


class MySchema(ExpandableSchemaMixin, Schema):
    id = fields.Int()
    attr1 = fields.Str()
    attr2 = fields.Str()
    attr3 = ExpandableNested('MyNestedSchema')
    attr4 = ExpandableNested(AnotherNestedSchema, many=True)


class MyNestedSchema(ExpandableSchemaMixin, Schema):
    id = fields.Int()
    attr3 = fields.Str()
    attr4 = fields.Str()
    attr7 = ExpandableNested('self')

    class Meta:
        retrieve = get_my_nested_schema, ['id']
        batch = get_my_nested_schema_batch, [('id', 'ids')]


sample_json = dict(
    id=1,
    attr1='banana',
    attr2='potato',
    attr3=dict(
        id=4
    ),
    attr4=[
        dict(id=1), dict(id=2), dict(id=3)
    ]
)


class TestExpandableSchemaMixin:
    def test_serialize(self):
        result, errors = MySchema(expand=['attr3']).dump(sample_json)

        expected_result = dict(
            id=1,
            attr1='banana',
            attr2='potato',
            attr3=dict(
                id=4,
                attr3='pine-4',
                attr4='pineapple-4',
                attr7={'id': 7}
            ),
            attr4=[
                dict(id=1), dict(id=2), dict(id=3)
            ]
        )

        assert expected_result == result

    def test_serialize_many(self):
        result, errors = MySchema(expand=['attr4']).dump(sample_json)

        expected_result = dict(
            id=1,
            attr1='banana',
            attr2='potato',
            attr3=dict(
                id=4
            ),
            attr4=[
                dict(id=1, attr5='apple-1', attr6=[dict(id=1), dict(id=2)]),
                dict(id=2, attr5='apple-2', attr6=[dict(id=1), dict(id=2)]),
                dict(id=3, attr5='apple-3', attr6=[dict(id=1), dict(id=2)])
            ]
        )

        assert expected_result == result

    def test_serialize_many_nested(self):
        result, errors = MySchema(expand=['attr4.attr6', 'attr3']).dump(sample_json)

        expected_result = dict(
            id=1,
            attr1='banana',
            attr2='potato',
            attr3=dict(
                id=4,
                attr3='pine-4',
                attr4='pineapple-4',
                attr7={'id': 7}
            ),
            attr4=[
                dict(id=1, attr5='apple-1', attr6=[dict(id=1, attr3='pine-1', attr7={'id': 7}, attr4='pineapple-1'),
                                                   dict(id=2, attr3='pine-2', attr7={'id': 7}, attr4='pineapple-2')]),
                dict(id=2, attr5='apple-2', attr6=[dict(id=1, attr3='pine-1', attr7={'id': 7}, attr4='pineapple-1'),
                                                   dict(id=2, attr3='pine-2', attr7={'id': 7}, attr4='pineapple-2')]),
                dict(id=3, attr5='apple-3', attr6=[dict(id=1, attr3='pine-1', attr7={'id': 7}, attr4='pineapple-1'),
                                                   dict(id=2, attr3='pine-2', attr7={'id': 7}, attr4='pineapple-2')])
            ]
        )

        assert expected_result == result

    def test_three_levels_of_nesting(self):
        sample_json = dict(
            id=1,
            attr1='banana',
            attr2='potato',
            attr3=dict(
                id=4
            ),
            attr4=[
                dict(id=1)
            ]
        )

        samey = {'id': 7, 'attr3': 'pine-7', 'attr4': 'pineapple-7', 'attr7': {'id': 7}}

        result, errors = MySchema(expand=['attr4.attr6.attr7']).dump(sample_json)

        expected_result = dict(
            id=1,
            attr1='banana',
            attr2='potato',
            attr3=dict(
                id=4
            ),
            attr4=[
                dict(id=1, attr5='apple-1', attr6=[dict(id=1, attr3='pine-1', attr7=samey, attr4='pineapple-1'),
                                                   dict(id=2, attr3='pine-2', attr7=samey, attr4='pineapple-2')]),
            ]
        )

        assert expected_result == result

    def test_if_batch_function_is_present_then_use_the_batch_version(self):
        pass


class TestArgumentBuilder:
    def test_build_arguments_given_a_map(self):
        resource = {
            'id': 10,
            'fruit': 'banana',
            'something': 'else'
        }

        argument_map = {'id': 'resource_id', 'fruit': 'apple'}

        arguments = ArgumentBuilder().build_arguments(resource, argument_map)
        assert 10 == arguments['resource_id']
        assert 'banana' == arguments['apple']

    def test_aggregate_the_results(self):
        resource_1 = {
            'id': 10,
            'fruit': 'banana',
            'something': 'else'
        }
        resource_2 = {
            'id': 11,
            'fruit': 'melon',
            'something': 'else'
        }
        resource_3 = {
            'id': 12,
            'fruit': 'orange',
            'something': 'else'
        }

        argument_map = {'id': 'resource_id', 'fruit': 'apple'}

        arguments = ArgumentBuilder().build_arguments([resource_1, resource_2, resource_3], argument_map, many=True, aggregate=True)
        assert [10, 11, 12] == arguments['resource_id']
        assert ['banana', 'melon', 'orange'] == arguments['apple']

    def test_return_set_when_not_aggregating_the_results(self):
        resource_1 = {
            'id': 10,
            'fruit': 'banana',
            'something': 'else'
        }
        resource_2 = {
            'id': 11,
            'fruit': 'melon',
            'something': 'else'
        }
        resource_3 = {
            'id': 12,
            'fruit': 'orange',
            'something': 'else'
        }

        argument_map = {'id': 'resource_id', 'fruit': 'apple'}

        argument_set = ArgumentBuilder().build_arguments([resource_1, resource_2, resource_3], argument_map, many=True)
        expected_argument_set = [dict(resource_id=10, apple='banana'), dict(resource_id=11, apple='melon'), dict(resource_id=12, apple='orange')]

        for expected_argument in expected_argument_set:
            assert expected_argument in argument_set
