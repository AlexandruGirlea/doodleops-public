### How to not commit migrations:
This is intended to be used when doing local development and we don't want to 
commit migrations to the repository.


```bash
find . -path '*/migrations/*.py' -not -name '__init__.py' -delete && find . -path '*/migrations/*.pyc'  -delete
git rm -r --cached \*/migrations/\*
```