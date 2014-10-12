from copy import copy


class BaseObj(object):

    def __unicode__(self):
        return self.data

    def __init__(self, data, **kwargs):
        self.data = copy(data)


class Svg(BaseObj):
    pass


class Html(BaseObj):

    def __init__(self, data, **kwargs):

        if type(data) == str or type(data) == unicode:
            self.data = data

        # Support IPython notebook aware objects
        elif hasattr(data, '_repr_html_'):
            self.data = data._repr_html_()
