import uvicorn
from apiserver.env import app_port


def run():
    """ Run function for use in development environment. """
    uvicorn.run("apiserver.app:app", host="127.0.0.1", port=app_port, reload=True)


if __name__ == '__main__':
    run()
