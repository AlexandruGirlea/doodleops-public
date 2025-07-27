from rapidfuzz import fuzz
from django.http import Http404
from django.shortcuts import render, redirect
from django.db.models import Prefetch
from django.forms.models import model_to_dict
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from app_api.models import APIApp, API
from app_pages.forms import SuggestNewFeatureForm
from app_pages.models import BlogCategory, BlogPost
from app_settings.utils import get_setting
from common.other import get_no_of_free_credits_at_account_creation


def index(request, api_app_url_path=None):
    """
    `api_app_url_path` is used to help filter the APIs that are displayed on the
    index page based on the API APP Name (Category).
    """
    if request.session.get("oauth_next"):
        next_page = request.session.get("oauth_next")
        request.session["oauth_next"] = None
        return redirect(next_page)

    user_obj = None
    if request.user.is_authenticated:
        user_obj = request.user

    api_apps = APIApp.objects.prefetch_related(
        Prefetch(
            lookup="apis",
            queryset=(
                API.objects.all().order_by("display_order")
                if user_obj and user_obj.is_staff
                else API.objects.filter(active=True).order_by("display_order")
            )
        ),
    ).order_by("display_order")

    if user_obj and user_obj.is_staff:
        api_app_dict = {
            api_app.display_name: {
                "url_path": api_app.url_path,
                "apis": [
                    model_to_dict(api) for api in api_app.apis.all()
                ],
            }
            for api_app in api_apps if api_app.apis.all()
        }
    else:
        api_app_dict = {
            api_app.display_name: {
                "url_path": api_app.url_path,
                "apis": [
                    model_to_dict(api) for api in api_app.apis.all() if api.active
                ],
            }
            for api_app in api_apps if api_app.apis.filter(active=True).exists()
        }
    
    app_url_path = api_app_dict.get("AI", {}).get("url_path")
    ai_api = api_app_dict.get("AI", {}).get("apis", [])
    ai_api_url_path = ai_api[0].get("url_path") if ai_api else None

    return render(
        request=request,
        template_name="index.html",
        context={
            "app_url_path": app_url_path,
            "ai_api_url_path": ai_api_url_path,
            "no_of_free_credits": get_no_of_free_credits_at_account_creation(),
            "ai_api_other_info": ai_api[0].get("other_info") if ai_api else None
        },
    )


def services(request, api_app_url_path=None):
    """
    `api_app_url_path` is used to help filter the APIs that are displayed on the
    services page based on the API APP Name (Category).
    """
    if request.session.get("oauth_next"):
        next_page = request.session.get("oauth_next")
        request.session["oauth_next"] = None
        return redirect(next_page)
    
    user_obj = None
    if request.user.is_authenticated:
        user_obj = request.user
    
    api_apps = APIApp.objects.prefetch_related(
        Prefetch(
            lookup="apis",
            queryset=(
                API.objects.all().order_by("display_order")
                if user_obj and user_obj.is_staff
                else API.objects.filter(active=True).order_by("display_order")
            )
        ),
    ).order_by("display_order")
    
    if user_obj and user_obj.is_staff:
        api_app_dict = {
            api_app.display_name: {
                "url_path": api_app.url_path,
                "apis": [
                    model_to_dict(api) for api in api_app.apis.all()
                ],
            }
            for api_app in api_apps if api_app.apis.all()
        }
    else:
        api_app_dict = {
            api_app.display_name: {
                "url_path": api_app.url_path,
                "apis": [
                    model_to_dict(api) for api in api_app.apis.all() if api.active
                ],
            }
            for api_app in api_apps if api_app.apis.filter(active=True).exists()
        }
    
    return render(
        request=request,
        template_name="services.html",
        context={
            "api_app_dict": api_app_dict,
            "api_app_url_path": api_app_url_path,
            "chatgpt_link": get_setting(
                key="chatgpt_link", default="https://chatgpt.com/gpts"
            ),
            "no_of_free_credits": get_no_of_free_credits_at_account_creation()
        },
    )


def search_apis(request):
    query = request.GET.get('q', '').strip()
    apis = API.objects.filter(active=True)

    if query:
        query = query.lower()
        search_results = []
        for api in apis:
            display_name_score = fuzz.partial_ratio(
                query, api.display_name.lower()
            )
            description_score = fuzz.partial_ratio(
                query, api.description.lower() or ''
            )

            # You can adjust the weighting of display_name and description
            total_score = max(display_name_score, description_score)

            # Set a threshold for inclusion
            if total_score > 90:  # Adjust threshold as needed
                search_results.append((total_score, api))

        # Sort APIs by similarity score in descending order
        search_results.sort(key=lambda x: x[0], reverse=True)

        # Extract the APIs from the search results
        apis = [api for score, api in search_results]
    else:
        return redirect('services')

    context = {
        'apis': apis,
        'query': query,
    }
    return render(request, 'services.html', context)


def suggest_new_feature(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect('login')

        form = SuggestNewFeatureForm(request.POST)
        form.instance.user = request.user

        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Thank you for your suggestion {request.user.email}. We will "
                "review it shortly."
            )
            return redirect('suggest_new_feature')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SuggestNewFeatureForm()
    return render(request, 'suggest_new_feature.html', {'form': form})


def blog(request):
    if request.method != "GET":
        raise Http404

    # check if category is passed in the URL
    category_id = request.GET.get("category-id")
    if category_id:
        category = BlogCategory.objects.filter(pk=category_id).first()
        if not category:
            raise Http404

        blog_posts = BlogPost.objects.filter(
            category__pk=category_id
        ).order_by("-created_at")
    else:
        blog_posts = BlogPost.objects.all().order_by("-created_at")

    page_number = request.GET.get("page")

    paginator = Paginator(blog_posts, 5)

    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    if not page_obj.object_list and page_number != "1":
        return redirect(request.path + "?page=1")

    return render(
        request, "blog.html", {
            "category_name": category.name if category_id else "All",
            "page_obj": page_obj
        }
    )


def about(request):
    return render(request, "about.html")


def terms(request):
    return render(request, "terms_and_conditions.html")


def privacy(request):
    return render(request, "privacy.html")


def cookie_policy(request):
    return render(request, "cookie_policy.html")


def custom_404_view(request, exception=None):
    return render(request, '404.html', status=404)


def custom_500_view(request):
    return render(request, '500.html', status=500)


def custom_400_view(request, exception=None):
    return render(request, '400.html', status=400)


def custom_403_view(request, exception=None):
    return render(request, '403.html', status=403)


@login_required
def custom_admin_login_redirect(request):
    return redirect('admin:index')
