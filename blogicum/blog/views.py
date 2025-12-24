from django.http import Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.core.paginator import Paginator

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from .models import Category, Post, Comment
from .forms import PostForm, CommentForm, ProfileForm

from django.db.models import Count


def get_page(request, queryset, per_page=10):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def prepare_posts(queryset, filter_published=True):
    if filter_published:
        queryset = queryset.filter(
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now()
        )

    return queryset.annotate(
        comment_count=Count('comments')
    ).order_by(*Post._meta.ordering)


def index(request):
    posts = Post.objects.select_related('location', 'category', 'author')
    posts = prepare_posts(posts, filter_published=True)
    page_obj = get_page(request, posts)

    context = {
        'page_obj': page_obj
    }
    return render(request, 'blog/index.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(
        Post,
        pk=post_id,
    )

    if post.author != request.user:
        if (
            not post.is_published
            or not post.category.is_published
            or post.pub_date > timezone.now()
        ):
            raise Http404

    comment = post.comments.select_related('author').all()
    form = CommentForm()

    context = {
        'post': post,
        'comments': comment,
        'form': form
    }
    return render(request, 'blog/detail.html', context)


def category_posts(request, category_slug):
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )
    posts = category.posts.select_related(
        'location', 'category', 'author'
    )

    posts = prepare_posts(posts, filter_published=True)
    page_obj = get_page(request, posts)

    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, 'blog/category.html', context)


def profile(request, username):
    profile = get_object_or_404(User, username=username)

    if request.user == profile:
        posts = prepare_posts(
            Post.objects.filter(author=profile),
            filter_published=False
        )
    else:
        posts = prepare_posts(
            Post.objects.filter(author=profile),
            filter_published=True
        )

    page_obj = get_page(request, posts)

    context = {
        'profile': profile,
        'page_obj': page_obj
    }
    return render(request, 'blog/profile.html', context)


@login_required
def edit_profile(request):
    user = request.user
    form = ProfileForm(request.POST or None, instance=user)

    if not form.is_valid():
        return render(request, 'blog/user.html', {'form': form})

    form.save()
    return redirect('blog:profile', username=user.username)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, request.FILES or None)

    if not form.is_valid():
        return render(request, 'blog/create.html', {'form': form})

    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('blog:profile', username=request.user.username)


# @login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)

    form = PostForm(request.POST or None, request.FILES or None, instance=post)

    if not form.is_valid():
        return render(request, 'blog/create.html', {'form': form, 'post': post})

    form.save()
    return redirect('blog:post_detail', post_id=post_id)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    form = CommentForm(request.POST or None)

    if not form.is_valid():
        return redirect('blog:post_detail', post_id=post_id)

    comment = form.save(commit=False)
    comment.author = request.user
    comment.post = post
    comment.save()

    return redirect('blog:post_detail', post_id=post_id)


@login_required
def edit_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id)

    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)

    form = CommentForm(request.POST or None, instance=comment)

    if not form.is_valid():
        return render(
            request,
            'blog/comment.html',
            {'form': form, 'comment': comment}
        )

    form.save()
    return redirect('blog:post_detail', post_id=post_id)


@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)

    form = PostForm(request.POST or None, request.FILES or None, instance=post)

    if request.POST:
        post.delete()
        return redirect('blog:profile', username=request.user.username)

    return render(
        request,
        'blog/create.html',
        {'form': form, 'post': post}
    )



@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id)

    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)

    if request.POST:
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)

    return render(request, 'blog/comment.html', {'comment': comment})
