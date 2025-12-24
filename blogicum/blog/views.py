from django.http import Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.core.paginator import Paginator

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from .models import Category, Post, Comment
from .forms import PostForm, CommentForm, ProfileForm

from django.db.models import Count


def index(request):
    posts = Post.objects.select_related(
        'location', 'category', 'author'
    ).annotate(comment_count=Count('comments')).filter(
        pub_date__lte=timezone.now(),
        is_published=True,
        category__is_published=True
    ).order_by('-pub_date')

    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj
    }
    return render(request, 'blog/index.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(
        Post,
        pk=post_id,
        # is_published=True,
        # category__is_published=True,
        # pub_date__lte=timezone.now()
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
    ).annotate(comment_count=Count('comments')).filter(
        pub_date__lte=timezone.now(),
        is_published=True
    ).order_by('-pub_date')

    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, 'blog/category.html', context)


def profile(request, username):
    profile = get_object_or_404(User, username=username)

    if request.user == profile:
        posts = Post.objects.filter(author=profile)
    else:
        posts = Post.objects.filter(
            author=profile,
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now()
        )

    posts = posts.annotate(comment_count=Count('comments')
                           ).order_by('-pub_date')

    print(posts.query)
    print(posts.count())

    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'profile': profile,
        'page_obj': page_obj
    }
    return render(request, 'blog/profile.html', context)


@login_required
def edit_profile(request):
    user = request.user
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('blog:profile', username=user.username)
    else:
        form = ProfileForm(instance=user)
    return render(request, 'blog/user.html', {'form': form})


@login_required
def post_create(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('blog:profile', username=request.user.username)

    else:
        form = PostForm()
    return render(request, 'blog/create.html', {'form': form})


# @login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', post_id=post_id)
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/create.html', {'form': form, 'post': post})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
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

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('blog:post_detail', post_id=post_id)
    else:
        form = CommentForm(instance=comment)

    return render(
        request,
        'blog/comment.html',
        {'form': form, 'comment': comment}
    )


@login_required
def post_delete(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)
    if request.method == 'POST':
        post.delete()
        return redirect('blog:profile', username=request.user.username)
    form = PostForm(instance=post)
    return render(request, 'blog/create.html', {'form': form, 'post': post})


@login_required
def delete_comment(request, post_id, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id, post_id=post_id)

    # Только автор комментария
    if comment.author != request.user:
        return redirect('blog:post_detail', post_id=post_id)

    if request.method == 'POST':
        comment.delete()
        return redirect('blog:post_detail', post_id=post_id)

    # ВАЖНО: НЕ передаём form!
    return render(
        request,
        'blog/comment.html',
        {'comment': comment}
    )
