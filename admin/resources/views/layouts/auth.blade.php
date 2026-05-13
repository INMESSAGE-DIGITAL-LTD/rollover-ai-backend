<!DOCTYPE html>
<html lang="en" class="no-js">
    <!-- Head -->
    <head>
        <title>Sign In | {{ get_option('site_title') }}</title>

        <!-- Meta -->
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <meta http-equiv="x-ua-compatible" content="ie=edge">
        <meta name="keywords" content="{{ get_option('site_title') }}">
        <meta name="description" content="{{ get_option('site_title') }}">
        <meta name="author" content="{{ url('/') }}">

        <!-- Favicon -->
        <link rel="shortcut icon" href="{{ get_icon() }}" type="image/x-icon">

        <!-- Web Fonts -->
        <link href="//fonts.googleapis.com/css?family=Open+Sans:300,400,600,700" rel="stylesheet">

        <!-- Components Vendor Styles -->
        <link rel="stylesheet" href="{{ asset('public/auth/vendor/font-awesome/css/all.min.css') }}">

        <link rel="stylesheet" href="{{ asset('public/auth/vendor/bootstrap/bootstrap.css') }}">

        <!-- Theme Styles -->
        <link rel="stylesheet" href="{{ asset('public/auth/css/theme.css') }}">
    </head>
    <!-- End Head -->

    <body>
        <main class="container-fluid w-100" role="main">
            <div class="row">
                <div class="col-lg-6 d-flex flex-column justify-content-center align-items-center bg-white mnh-100vh">
                    <a class="u-login-form py-3 mb-auto" href="index.html">
                        <img class="img-fluid" src="{{ get_logo() }}" width="160" alt="{{ get_option('site_title') }}">
                    </a>
                    @yield('content')
                    
                </div>

                <div class="col-lg-6 d-none d-lg-flex flex-column align-items-center justify-content-center bg-light">
                    <img class="img-fluid position-relative u-z-index-3 mx-5" src="{{ asset('public/auth/svg/mockups/mockup.svg') }}" alt="Image description">

                    <figure class="u-shape u-shape--top-right u-shape--position-5">
                        <img src="{{ asset('public/auth/svg/shapes/shape-1.svg') }}" alt="Image description">
                    </figure>
                    <figure class="u-shape u-shape--center-left u-shape--position-6">
                        <img src="{{ asset('public/auth/svg/shapes/shape-2.svg') }}" alt="Image description">
                    </figure>
                    <figure class="u-shape u-shape--center-right u-shape--position-7">
                        <img src="{{ asset('public/auth/svg/shapes/shape-3.svg') }}" alt="Image description">
                    </figure>
                    <figure class="u-shape u-shape--bottom-left u-shape--position-8">
                        <img src="{{ asset('public/auth/svg/shapes/shape-4.svg') }}" alt="Image description">
                    </figure>
                </div>
            </div>
        </main>
    </body>
</html>