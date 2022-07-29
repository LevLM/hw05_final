import datetime


def year(request):
    dt = datetime.datetime.today()
    return {
        'year': dt.year
    }
