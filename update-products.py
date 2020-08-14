from tp.models import *

for prod in Product.objects.all():
    prod.sid = prod.cid.site
    prod.save()
