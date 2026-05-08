@extends('layouts.auth')

@section('content')
<div class="u-login-form">
    <form class="mb-3" action="{{ route('login') }}" method="post">
        @csrf
        @if(Session::has('error'))
        <div class="alert alert-danger">
            <strong class="mr-2">Danger!</strong>  {{ session('error') }}
        </div>
        @endif
        <div class="mb-3">
            <h1 class="h2">Welcome Back!</h1>
            <p class="small">Login to your dashboard with your registered email address and password.</p>
        </div>

        <div class="form-group mb-4">
            <label for="email">Your email</label>
            <input id="email" class="form-control" name="email" type="email" placeholder="john.doe@example.com" value="{{ old('email') }}">
        </div>

        <div class="form-group mb-4">
            <label for="password">Password</label>
            <input id="password" class="form-control" name="password" type="password" placeholder="Your password">
        </div>

        <div class="form-group d-flex justify-content-between align-items-center mb-4">
            <div class="custom-control custom-checkbox">
                <input id="remember" class="custom-control-input" name="remember" type="checkbox">
                <label class="custom-control-label" for="remember">Remember me</label>
            </div>
            @if (Route::has('password.request'))
            <a class="link-muted small" href="{{ route('password.request') }}">Forgot Password?</a>
            @endif
        </div>

        <button class="btn btn-primary btn-block" type="submit">Login</button>
    </form>

    {{-- <p class="small">
        Don’t have an account? <a href="account-sign-up.html">Sign Up here</a>
    </p> --}}
</div>

<div class="u-login-form text-muted py-3 mt-auto">
    <small><i class="far fa-question-circle mr-1"></i>  </small>
</div>
@endsection