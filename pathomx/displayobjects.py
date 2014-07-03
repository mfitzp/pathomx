

class BaseObj(object):

    def __unicode__(self):
        return self.data

    def __init__(self, data, **kwargs):
        self.data = data


class Svg(BaseObj):
    pass


class Html(BaseObj):
    pass
