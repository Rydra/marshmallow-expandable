# Marshmallow-expandable

# Why Marshmallow?

Most python web frameworks want to couple you too much to their ways.
They want you to marry them "too much", causing serious vendor lock-in
issues as the size of your project increases.
Marshmallow is a serializing library with the aim of working everywhere
and being framework agnostic, and we love both Marshmallow and Uncle Bob's
Clean Architecture for it. Check more about [Marshmallow](https://marshmallow.readthedocs.io/en/3.0/why.html)
and the [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html), you won't be disappointed!

# Why Marshmallow-expandable?

Some REST apis expose some kind of resource expander, that allows your API consumers
to retrieve a resource and all its associated resources in a single HTTP call.

Marshmallow-expandable allows you to serialize your domain entities and expand
their nested relationships when serializing.

# Specifics

Marshmallow-expandable is intended to play nice with Marshmallow and any other
plugins. You only need to make your Schema classes inherit the `ExpandableSchemaMixin`
and use the `ExpandableNested` to leverage its power.

# Complete example

Suppose we have the following Marshmallow schemas:

```python
class BookSchema(Schema):
    id = fields.Int()
    author = fields.Nested('AuthorSchema')
    name = fields.Str()

class PublisherSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    published_books = fields.Nested(BookSchema, many=True)

class AuthorSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    publisher = fields.Nested(PublisherSchema)
    books = fields.Nested(BookSchema, many=True)
```

Hopefully the example is simple to understand. An author may author some books
and it is associated with publisher company, which also have published some books.

A well designed REST API should be built around the concept of resource. In this example
suppose you have three resources, Book, Publisher and Author. If you want to get a book from your
API you would typically receive the following response:

```
GET /api/books/1
{
    "id": 1,
    "author": {
        "href": "/api/authors/10"
        "id": 10
    },
    "name": "The name of the wind"
}
```

But what if you want to request more information about an author? You would need to make another
call to GET /api/authors/10 to get the author resource. And you can go deeper, asking for the publisher
of that author, and well, the rest is history. With enough endpoints and nested graphs the performance
of your clients can go down pretty quickly.

But with marshmallow-expandable you could do a GET request like and you could go farther:
```
GET /api/books/1?expand=author
{
    "id": 1,
    "author": {
        "href": "/api/authors/10"
        "id": 10,
        "name": "Patrick Rothfuss"
        "publisher": {
            "href": "/api/publishers/11"
            "id": 11
        },
        books: [
            {"href": "/api/books/1", "id": 1}, {"href": "/api/books/2", "id": 2}
        ]
    },
    "name": "The name of the wind"
}
```

And even farther:
```
GET /api/books/1?expand=author.publisher, author.books
{
    "id": 1,
    "author": {
        "href": "/api/authors/10"
        "id": 10,
        "name": "Patrick Rothfuss"
        "publisher": {
            "href": "/api/publishers/11"
            "id": 11,
            "name": "Some publisher name",
            "published_books": {"href": "/api/books/1", "id": 1}, {"href": "/api/books/2", "id": 2}
        },
        books: [
            {
                "href": "/api/books/1", "id": 1, "author": {"href": "/api/authors/10", "id": 10}, "name": "The name of the wind"}
            },
            {
                "href": "/api/books/2", "id": 2, "author": {"href": "/api/authors/10", "id": 10}, "name": "The wise man's fear"}
            }
        ]
    },
    "name": "The name of the wind"
}
```

You get the idea of resource expansion. This brings your API to a next level, while keeping you
agnostic of the framework: no coupling to Django, nor Flask, nor Tornado, only your beloved Marshmallow.

## How to achieve this?

The serialization library you should be using to achieve this must be obviously Marshmallow. You need
to change your schemas this way:

```python
class BookSchema(ExpandableSchemaMixin, Schema):
    id = fields.Int()
    author = ExpandableNested('AuthorSchema')
    name = fields.Str()
    
    class Meta:
        retrieve = get_book, ['id']

class PublisherSchema(ExpandableSchemaMixin, Schema):
    id = fields.Int()
    name = fields.Str()
    published_books = ExpandableNested(BookSchema, many=True)
    
    class Meta:
        retrieve = get_publisher, ['id']

class AuthorSchema(ExpandableSchemaMixin, Schema):
    id = fields.Int()
    name = fields.Str()
    publisher = ExpandableNested(PublisherSchema)
    books = ExpandableNested(BookSchema, many=True)
    
    class Meta:
        retrieve = get_author, ['id']
```

In a nutshell:

- Make your schemas inherit the `ExpandableSchemaMixin`
- Replace all Nested fields for `ExpandableNested` type of field. `ExpandableNested`
inherits `Nested` field from Marshmallow, so it will play nicely.
- You need to create a `Meta` class inside the Schema, and include the field
`retrieve`. Retrieve requires a tuple of two elements, the first element being the function from
where to obtain the resource, and the value mapping from the resource to the function.

With these elements in place, you can serialize your resources this way:

```python
result, errors = BookSchema(expand=['author', 'author.publisher']).dump(my_book_resource)
```

In the `result` variable you will obtain the serialized book resource with the field author and subfield
publisher in it. Marshmallow-expandable will call the retrieve methods of the subresources you
want to expand as appropriate.

Check the 
[Zalando API guidelines](https://opensource.zalando.com/restful-api-guidelines/), they are
one of the best resources to learn how to design a good REST API


# Contributors are always welcome!

Feel free to fork this project and contribute back to it opening a pull request and making questions
or submitting ideas, questions or feature requests in the issues tab of Github!
