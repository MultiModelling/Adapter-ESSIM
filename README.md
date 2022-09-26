# MMvIB ESSIM Adapter

The API is available at http://localhost:9203/openapi

The project is based on TNO's Flask REST API template. For more information, see below.

## Container
Use: `docker-compose build` to build the image
Run the image using `docker-compose up -d`.


## Flask REST API Template

This is a skeleton application for a REST API. It contains a modular setup that should prevent annoying circular imports
that are sometimes an issue when scaling up Flask applications. It also contains a
generic library of code developed in other projects (under tno/shared).

The key dependencies are:

- [Flask-smorest](https://flask-smorest.readthedocs.io): A REST API framework built on top
  of [marshmallow](https://marshmallow.readthedocs.io/).

## Using the application

The application can run in Docker or locally. There is a docker-compose.infra.yml file which is meant for infrastructure
services, which are not part of your application. The purpose is to run that always, and then you can either use the
docker-compose.yml to start the API, or run it locally.

The Makefile contains a number of common commands. To get started, you can run `make dev` and it should build the Docker
image and start the API in Gunicorn with the automatic reloader. If you wish to use the Flask local dev server, either
modify the docker-compose.yml file or start it outside of Docker, for example with `make dev-local`.

Before running the application locally though, you are advised to create a virtual environment. Install the dependencies
using `pip install -r requirements.txt`, or `make requirements`. Then, copy the .env-template file to .env.

Either way, the API should start on http://localhost:9200. Access the autogenerated docs
through http://localhost:9200/openapi or http://localhost:9200/redoc.

## How to use this template

You would typically copy this template, and replace all instances of "flask_rest_api" with the name of your application.
Application specific code would then go under `tno/<your_application_name>/`. Adding code under `tno/shared` is of
course also possible, but keep in mind that the goal of that folder is to allow for sharing between multiple
repositories. A proper way to actually set that up still needs to be figured out though.

Your endpoints would go under `tno/<your_application_name/apis`, grouped by file. Don't forget to register your
blueprints in `tno/<your_application_name>/__init__.py`.

## Notable features

There is a very permissive setup of CORS, so that an arbitrary frontend can perform requests to this REST PAI.

The application contains a setup of structlog, a structured logging framework. This makes it trivial to perform more
advanced logging, and will by default output JSON logs in production and colored tab-separated logs in development.

For dependency management we use pip-tools, which is a combination of pip-compile (which generates a requirements.txt
from a requirements.in file) and pip-sync (which synchronizes your virtualenv to the exact state as specified in the
requirements.txt).

The configuration of Flask-Migrate set up to facilitate database migrations through Alembic.

There is a basic configuration of mypy (see mypy.ini) for static type checking.

## Design decisions

### Flask-smorest

Flask-smorest is but one option for REST APIs in Flask. It seems currently the most up to date option, and added bonuses
are that it is relatively lightweight, building on top of existing paradigms from Flask (such as Blueprints) and
building on top of marshmallow for schema validation.

Flask-Restless just generates REST-like API's for your database models. This is not really REST and can be quite
fragile.

Flask-RESTPlus is pretty nice and is very similar to Flask-smorest. It is heavier than Flask-smorest though, inventing
more of their own paradigms on top of Flask. It is hardly maintained though.

There is also Flask-RESTX, which is a fork of Flask-RESTPlus so is very similar. We've used it together with
flask-accepts, marshmallow, and marshmallow-dataclass for pretty nice results. However, Flask-smorest does not need any
of that because it just directly builds on top of marshmallow, so the end result is cleaner.