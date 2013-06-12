import datetime
import json
from django.contrib.gis.geos import GEOSGeometry
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.contrib.gis.geos import fromstr
from django.core.paginator import Paginator, PageNotAnInteger
from django.template.loader import render_to_string
from mussels.forms.observations import ObservationForm, WaterbodyForm, SubstrateForm, AgencyForm, SpecieForm, UserForm
from mussels.models import Observation, Agency, Waterbody, Specie, Substrate, User

model_to_form_class = {
    'waterbody': WaterbodyForm,
    'substrate': SubstrateForm,
    'agency': AgencyForm,
    'specie': SpecieForm,
    'user': UserForm, 
}

model_to_model_class = {
    'waterbody': Waterbody,
    'substrate': Substrate,
    'agency': Agency,
    'specie': Specie,
    'user': User,
}


def admin(request):
    return render(request, "observations/admin.html", {

    })

def view(request):
    observations = Observation.objects.all().select_related("waterbody", "agency", "specie", "user").prefetch_related("substrates")
    paginator = Paginator(observations, 100)

    page = request.GET.get('page')
    try:
        page = paginator.page(page)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    rendered = render(request, "observations/view.html", {
        'page': page,
    })

    return rendered

def edit(request, observation_id=None):
    """
    View for adding or editing a observation observation
    """
    instance = None
    if observation_id is not None:
        instance = get_object_or_404(Observation, observation_id=observation_id)

    if request.POST:
        form = ObservationForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Observation saved")
            return HttpResponseRedirect(reverse("observations-view"))
    else:
        form = ObservationForm(instance=instance)

    return render(request, 'observations/edit.html', {
        'form': form,
    })

def view_related_tables(request, model):
    model_class = model_to_model_class[model]
    objects = model_class.objects.all()
    return render(request, 'observations/view_related.html', {
        'objects': objects,
        'model': model,
    })

def edit_related_tables(request, model, pk=None):
    form_class = model_to_form_class[model]

    instance = None
    if pk is not None:
        instance = get_object_or_404(form_class.Meta.model, pk=pk)

    if request.POST:
        form = form_class(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, "Saved!")
            return HttpResponseRedirect(reverse("observations-view-related", args=(model,)))
    else:
        form = form_class(instance=instance)

    return render(request, 'observations/edit_related.html', {
        'form': form,
    })

def to_kml(request):
    rows = Observation.objects.search(specie="Dreissena r. bugensis")
    string = render_to_string("observations/_kml.kml", {"rows": rows})
    if request.GET:
        response = HttpResponse(string, content_type="text/xml")
    else:
        response = HttpResponse(string, content_type="application/vnd.google-earth.kml+xml; charset=utf-8")
    return response

def to_json(request):
    dthandler = lambda obj: obj.isoformat() if isinstance(obj, datetime.date) else None
    kwargs = {}
    for param in request.GET:
        if param.endswith("[]"):
            items = request.GET.getlist(param)
            kwargs[param[:-2]] = items
        else:
            kwargs[param] = request.GET[param]

    rows = Observation.objects.search(**kwargs)
    for row in rows:
        del row['the_geom']
        p = GEOSGeometry(row['the_geom_plain'])
        row['the_geom_plain'] = (p[0], p[1])
    return HttpResponse(json.dumps(rows, default=dthandler))
