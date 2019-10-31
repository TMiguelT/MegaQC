"""
Generic tests for normal resources that follow a schema for GET, POST, DELETE etc
"""
import pytest
from megaqc import graphql
from megaqc.model import models
from megaqc.user import models as user_models
from megaqc.extensions import db
from tests import factories
from flask import url_for
from marshmallow_jsonapi.fields import Relationship
from sqlalchemy import inspect
from graphene.utils.str_converters import to_camel_case
from graphene.test import Client
from graphene_sqlalchemy import SQLAlchemyObjectType, SQLAlchemyConnectionField
from gql_query_builder import GqlQuery
from inflection import camelize, underscore

all_factories = factories.BaseFactory.__subclasses__()


@pytest.fixture()
def graphql_client():
    return Client(graphql.schema)


def find_factory(model):
    for factory in all_factories:
        if factory._meta.model == model:
            return factory


def instance_pk(instance):
    column_name = inspect(instance.__class__).primary_key[0].name
    return column_name, getattr(instance, column_name)


@pytest.mark.parametrize('name, connection', [(name, query) for name, query in
                                              vars(graphql.schema._query).items() if
                                              isinstance(query,
                                                         SQLAlchemyConnectionField)])
def test_get_many_resources_new(name, connection, session, graphql_client, admin_token):
    factory = find_factory(connection.model)

    # Construct an instance of the model
    instance = factory()
    session.commit()

    fields = [camelize(field.name, uppercase_first_letter=False) for field in inspect(connection.model).columns]
    type_name = camelize(name, uppercase_first_letter=False)

    query = GqlQuery().fields([
        GqlQuery().fields([
            GqlQuery().fields(fields).query('node').generate()
        ]).query('edges').generate()
    ]).query(type_name).operation().generate()

    # Do the request
    result = graphql_client.execute(query)

    # Check the request was successful
    assert 'data' in result and 'errors' not in result

    # Check we got one node back
    assert len(result['data'][type_name]['edges']) == 1

    single_result = result['data'][type_name]['edges'][0]['node']

    # All keys in the response data should be a subset of the keys in the model
    for key, value in single_result.items():
        snake_key = underscore(key)
        assert hasattr(instance, snake_key)
        instance_val = getattr(instance, snake_key)

        if isinstance(instance_val, db.Model):
            assert instance_val.primary_key == value
        else:
            assert (instance_val == value or value == str(instance_val))

#
# @pytest.mark.parametrize(['resource', 'parent_model'], [
#     [views.UploadList, user_models.User],
#     [views.ReportList, user_models.User],
#     [views.ReportMetaList, models.Report],
#     [views.SampleList, models.Report],
#     [views.SampleDataList, models.Sample],
#     [views.FilterList, user_models.User],
#     [views.FavouritePlotList, user_models.User],
#     [views.DashboardList, user_models.User]
# ])
# def test_get_many_resources_associated(resource, parent_model, session, client, admin_token, app):
#     """
#     Tests a list resource that is the child of another resource, e.g. /reports/1/samples
#     """
#     factory = find_factory(resource.model)
#
#     # The rule object gives us access to URL parameters
#     rule = app.url_map._rules_by_endpoint['rest_api.' + resource.endpoint][0]
#
#     # Construct an instance of the model
#     instance = factory()
#     session.commit()
#
#     # Do the request
#     url = url_for('rest_api.' + resource.endpoint, **{key: getattr(instance, key) for key in rule.arguments})
#     rv = client.get(url, headers={'access_token': admin_token})
#
#     # Check the request was successful
#     assert rv.status_code == 200
#
#     # This also does data validation
#     data = resource.schema(many=True).load(rv.json)
#
#     # Check we got at least the instance we created
#     assert len(data) > 0
#
#     # All keys in the response data should be a subset of the keys in the model
#     # dict.items() acts as a set object here: https://docs.python.org/3/library/stdtypes.html#dictionary-view-objects
#     for key, value in data[-1].items():
#         assert hasattr(instance, key)
#         instance_val = getattr(instance, key)
#
#         if isinstance(instance_val, db.Model):
#             assert instance_val.primary_key == value
#         else:
#             assert instance_val == value
#
# @pytest.mark.parametrize('resource', [
#     views.UploadList,
#     views.ReportList,
#     views.ReportMetaList,
#     views.SampleList,
#     views.ReportMetaTypeList,
#     views.DataTypeList,
#     views.UserList,
#     views.FilterList,
#     views.FilterGroupList,
#     views.FavouritePlotList,
#     views.DashboardList
# ])
# def test_post_resource(resource, admin_token, session, client):
#     """
#     POST /resources
#     """
#
#     # Construct an instance of the model
#     factory = find_factory(resource.model)
#     instance = factory()
#
#     # Remove the object from the database, because we're going to submit it via the API
#     session.expunge_all()
#     # session.expunge(instance)
#     session.commit()
#
#     # Work out which fields are relationships, so we can attach all of it in the request
#     relationships = set([key for key, value in resource.schema._declared_fields.items() if isinstance(value, Relationship)])
#
#     # Serialize it
#     # TODO: work out how to include all relationships, not just top level ones
#     request = resource.schema(many=False, use_links=False, include_data='linkage_recursive').dump(instance)
#
#     count_1 = session.query(resource.model).count()
#
#     # Do the request
#     url = url_for('rest_api.' + resource.endpoint)
#     rv = client.post(url, json=request, headers={'access_token': admin_token})
#
#     # Check the request was successful
#     assert rv.status_code == 201
#
#     # Check that we now have data
#     count_2 = session.query(resource.model).count()
#     assert count_2 - count_1 == 1
#
#     # Validate the returned data
#     data = resource.schema(many=False).load(rv.json)
# @pytest.mark.parametrize(argnames, [
#     argvalues['report'],
#     argvalues['upload'],
#     argvalues['sample'],
#     argvalues['filter'],
#     argvalues['user'],
#     argvalues['sample_data'],
#     argvalues['report_meta'],
#     argvalues['sample_data_type'],
#     argvalues['filter_group'],
#     argvalues['favourite'],
#     argvalues['dashboard'],
# ])
# def test_get_many_resources(client, single_endpoint, many_endpoint, schema, factory, id_field, admin_token, model,
#                             no_post, session):
#     """
#     GET /resources
#     """
#
#     # Construct an instance of the model
#     instance = factory()
#     session.commit()
#
#     # Do the request
#     rv = client.get(many_endpoint(instance), headers={'access_token': admin_token})
#
#     # Check the request was successful
#     assert rv.status_code == 200
#
#     # This also does data validation
#     data = schema(many=True).load(rv.json)
#
#     # Check we got at least the instance we created
#     assert len(data) > 0
#
#     # And it had the right ID
#     assert data[-1][id_field] == str(getattr(instance, id_field))
#
#
# # We can't post samples, reports or uploads in the normal way, so don't test them here
# @pytest.mark.parametrize(argnames, [
#     argvalues['filter'],
#     argvalues['user'],
#     argvalues['sample_data'],
#     argvalues['report_meta']
# ])
# def test_post_resource(client, single_endpoint, many_endpoint, schema, factory, id_field, admin_token, model, session,
#                        no_post):
#     """
#     POST /resources
#     """
#
#     # Construct an instance of the model
#     instance = factory()
#     if instance in session:
#         session.expunge(instance)
#     session.commit()
#
#     # Work out which fields are relationships
#     relationships = set([key for key, value in schema._declared_fields.items() if isinstance(value, Relationship)])
#     no_post = set(no_post)
#
#     # Serialize it
#     request = schema(many=False, use_links=False, exclude=no_post, include_data=relationships - no_post).dump(instance)
#
#     count_1 = session.query(model).count()
#
#     # Do the request
#     rv = client.post(many_endpoint(instance), json=request, headers={'access_token': admin_token})
#
#     # Check the request was successful
#     assert rv.status_code == 201
#
#     # Check that we now have data
#     count_2 = session.query(model).count()
#     assert count_2 - count_1 == 1
#
#     # Validate the returned data
#     data = schema(many=False).load(rv.json)
#
#
# @pytest.mark.parametrize(argnames, [
#     argvalues['report'],
#     argvalues['upload'],
#     argvalues['sample'],
#     argvalues['filter'],
#     argvalues['user']
# ])
# def test_delete_resource(session, client, single_endpoint, many_endpoint, schema, factory, id_field, model, token,
#                          admin_token, no_post):
#     """
#     DELETE /resources/1
#     """
#
#     # Construct an instance of the model
#     instance = factory()
#
#     count_1 = session.query(model).count()
#
#     # An admin should be able to delete anything (this doesn't test when resources shouldn't be deletable by regular
#     # users
#     rv = client.delete(single_endpoint(instance), headers={'access_token': admin_token})
#
#     # Check the request was successful, as an admin
#     assert rv.status_code == 200
#
#     # Check that we deleted the row from the DB
#     count_2 = session.query(model).count()
#     assert count_1 - count_2 == 1
#
#
# @pytest.mark.parametrize(argnames, [
#     argvalues['report'],
#     argvalues['upload'],
#     argvalues['sample'],
#     argvalues['filter'],
#     argvalues['user'],
#     argvalues['sample_data_type']
# ])
# def test_get_resource(session, client, single_endpoint, many_endpoint, schema, factory, id_field, model,
#                       admin_token, no_post):
#     """
#     GET /resources/1
#     """
#
#     # Construct an instance of the model
#     instance = factory()
#     session.add(instance)
#     session.commit()
#
#     # Do the request
#     rv = client.get(single_endpoint(instance), headers={'access_token': admin_token})
#
#     # Check the request was successful
#     assert rv.status_code == 200
#
#     # This also does data validation
#     data = schema(many=False).load(rv.json)
#
#     # And it had the right ID
#     assert data[id_field] == str(getattr(instance, id_field))
