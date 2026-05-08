<!DOCTYPE html>
<html lang="en" class="no-js">
<head>
	<title>{{ get_option('site_title') }}</title>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
	<meta http-equiv="x-ua-compatible" content="ie=edge">
	<meta name="keywords" content="{{ get_option('company_name') }}">
	<meta name="description" content="{{ get_option('company_name') }}">
	<meta name="author" content="{{ url('/') }}">
	<meta name="csrf-token" content="{{ csrf_token() }}">
	<meta name="referrer" content="no-referrer"/>

	<link rel="icon" href="{{ get_icon() }}" type="image/x-icon"/>
	<link href="//fonts.googleapis.com/css?family=Open+Sans:300,400,600,700" rel="stylesheet">
	<link rel="stylesheet" href="{{ asset('public/backend') }}/vendor/font-awesome/css/all.min.css">
	<link rel="stylesheet" href="{{ asset('public/backend') }}/vendor/malihu-custom-scrollbar-plugin/jquery.mCustomScrollbar.css">
	<link rel="stylesheet" href="{{ asset('public/backend/vendor/toastr/toastr.css') }}">
	<link rel="stylesheet" href="{{ asset('public/backend/vendor/dropify/dropify.min.css') }}">
	@if(!Request::is('dashboard'))
	<link rel="stylesheet" href="{{ asset('public/backend') }}/vendor/select2/dist/css/select2.min.css">
	<link rel="stylesheet" href="{{ asset('public/backend') }}/vendor/flatpickr/flatpickr.min.css">
	<link rel="stylesheet" href="{{ asset('public/backend/vendor/datatables/dataTables.bootstrap4.min.css') }}"/>
	<link rel="stylesheet" href="{{ asset('public/backend/vendor/datatables/buttons.bootstrap4.min.css') }}"/>
	<link rel="stylesheet" href="{{ asset('public/backend/vendor/datatables/responsive.bootstrap4.min.css') }}"/>
	<link rel="stylesheet" href="{{ asset('public/backend/vendor/bootstrap-datepicker/css/datepicker.css') }}">
	<link rel="stylesheet" href="{{ asset('public/backend/vendor/flatpickr/flatpickr.min.css') }}">
	<link rel="stylesheet" href="{{ asset('public/backend/vendor/summernote/summernote-bs4.min.css') }}">
	@endif
	<!-- Theme Styles -->
	<link rel="stylesheet" href="{{ asset('public/backend') }}/css/theme.css">
	<link rel="stylesheet" href="{{ asset('public/backend') }}/css/style.css">
	<style>
		.js-doughnut-chart {
			width: 70px !important;
			height: 70px !important;
		}
	</style>
	@include('layouts.others.variables')
</head>
<body>
	<div id="preloader"></div>
	<header class="u-header">
		<div class="u-header-left">
			<a class="u-header-logo" href="{{ url('dashboard') }}">
				<img class="u-logo-desktop" src="{{ get_logo() }}" width="160" alt="{{ get_option('company_name') }}">
				<img class="img-fluid u-logo-mobile" src="{{ get_icon() }}" width="50" alt="{{ get_option('company_name') }}">
			</a>
		</div>
		<div class="u-header-middle">
			<a class="js-sidebar-invoker u-sidebar-invoker" href="#!" data-is-close-all-except-this="true" data-target="#sidebar">
				<i class="fa fa-bars u-sidebar-invoker__icon--open"></i>
				<i class="fa fa-times u-sidebar-invoker__icon--close"></i>
			</a>
			<div class="u-header-search" data-search-mobile-invoker="#headerSearchMobileInvoker" data-search-target="#headerSearch">
				<a id="headerSearchMobileInvoker" class="btn btn-link input-group-prepend u-header-search__mobile-invoker" href="#!">
					<i class="fa fa-search"></i>
				</a>
				<div id="headerSearch" class="u-header-search-form">
					{{-- <form>
																<div class="input-group">
																	<button class="btn-link input-group-prepend u-header-search__btn" type="submit">
																		<i class="fa fa-search"></i>
																	</button>
																	<input class="form-control u-header-search__field" type="search" placeholder="Type to search…">
																</div>
															</form> --}}
				</div>
			</div>
		</div>
		<div class="u-header-right">
			<div class="dropdown ml-2">
				<a class="link-muted d-flex align-items-center" href="#!" role="button" id="dropdownMenuLink" aria-haspopup="true" aria-expanded="false" data-toggle="dropdown">
					<img class="u-avatar--xs img-fluid rounded-circle mr-2" src="{{ asset(user()->image) }}" alt="User Profile">
					<span class="text-dark d-none d-sm-inline-block">
						{{ user()->name }} <small class="fa fa-angle-down text-muted ml-1"></small>
					</span>
				</a>
				<div class="dropdown-menu dropdown-menu-right border-0 py-0 mt-3" aria-labelledby="dropdownMenuLink" style="width: 260px;">
					<div class="card">
						<div class="card-body">
							<ul class="list-unstyled mb-0">
								<li class="mb-4">
									<a class="d-flex align-items-center link-dark ajax-modal" href="{{ route('profile.show') }}" data-title="{{ _lang('Profile Details') }}">
										<span class="h3 mb-0"><i class="far fa-user-circle text-muted mr-3"></i></span> {{ _lang('View Profile') }}
									</a>
								</li>
								<li class="mb-4">
									<a class="d-flex align-items-center link-dark ajax-modal" href="{{ route('profile.edit') }}" data-title="{{ _lang('Edit Profile') }}">
										<span class="h3 mb-0"><i class="far fa-edit text-muted mr-3"></i></span> {{ _lang('Edit Profile') }}
									</a>
								</li>
								<li class="mb-4">
									<a class="d-flex align-items-center link-dark ajax-modal" href="{{ route('password.change') }}" data-title="{{ _lang('Change Password') }}">
										<span class="h3 mb-0"><i class="fas fa-lock text-muted mr-3"></i></span> {{ _lang('Change Password') }}
									</a>
								</li>
								<li>
									<a class="d-flex align-items-center link-dark" href="{{ url('logout') }}">
										<span class="h3 mb-0"><i class="far fa-share-square text-muted mr-3"></i></span> {{ _lang('Sign Out') }}
									</a>
								</li>
							</ul>
						</div>
					</div>
				</div>
			</div>
		</div>
	</header>
	<main class="u-main" role="main">
		<aside id="sidebar" class="u-sidebar">
			<div class="u-sidebar-inner">
				<header class="u-sidebar-header">
					<a class="u-sidebar-logo" href="{{ url('dashboard') }}">
						<img class="img-fluid" src="{{ get_logo() }}" width="124" alt="{{ get_option('company_name') }}">
					</a>
				</header>
				<nav class="u-sidebar-nav">
					<ul class="u-sidebar-nav-menu u-sidebar-nav-menu--top-level">
						<li class="u-sidebar-nav-menu__item">
							<a class="u-sidebar-nav-menu__link" href="{{ url('dashboard') }}">
								<i class="fa fa-cubes u-sidebar-nav-menu__item-icon"></i>
								<span class="u-sidebar-nav-menu__item-title">{{ _lang('Dashboard') }}</span>
							</a>
						</li>
						@include('layouts.menus.' . user()->user_type)
					</ul>
				</nav>
			</div>
		</aside>
		<!-- End Sidebar -->

		<div class="u-content">
			<div class="u-body">

				@if(!Request::is('dashboard'))
				<!-- End Breadcrumb -->
				<div class="mb-4 breadcrumb-main d-none">
					<nav aria-label="breadcrumb">
						<h1 class="h3 page-title">{{ _lang('Dashboard') }}</h1>
						<ol class="breadcrumb bg-transparent small p-0">
							<li class="breadcrumb-item" aria-current="page">
								<a href="{{ url('dashboard') }}"> {{ _lang('Dashboard') }}</a>
							</li>
							@php
							$segments = '';
							$request_segments = Request::segments();
							@endphp
							@foreach($request_segments as $key => $segment)
							@php
							if (is_numeric($segment))
								continue;
							$segments .= '/' . $segment;
							@endphp
							<li class="breadcrumb-item {{ (count($request_segments) - 1) == $key ? 'active' : '' }}" aria-current="page">
								<a href="{{ url($segments) }}">
									{{ ucwords(str_replace('_', ' ', $segment)) }}
								</a>
							</li>
							@endforeach
						</ol>
					</nav>
				</div>
				@endif
				@yield('content')
			</div>
			<footer class="u-footer d-md-flex align-items-md-center text-center text-md-left text-muted text-muted">
				<p class="h5 mb-0 ml-auto">
					&copy; 
					<a class="link-muted" href="{{ url('/') }}" target="_blank">{{ get_option('app_name') }}</a>. All Rights Reserved.
				</p>
			</footer>
		</div>
	</main>
	<div id="main_modal" class="modal fade" role="dialog" data-keyboard="false">
		<div class="modal-dialog modal-lg">
			<div class="modal-content">
				<div class="modal-header">
					<h5 class="modal-title"></h5>
					<button type="button" class="close float-right" data-dismiss="modal" aria-label="Close">
						<span aria-hidden="true">x</span>
					</button>
				</div>
				<div class="col-md-12">
					<div class="alert alert-danger" style="display:none; margin: 15px;"></div>
					<div class="alert alert-success" style="display:none; margin: 15px;"></div>
				</div>
				<div class="modal-body"></div>
			</div>
		</div>
	</div>

	<!-- Global Vendor -->
	<script src="{{ asset('public/backend/vendor/jquery/dist/jquery.min.js') }}"></script>
	<script src="{{ asset('public/backend/vendor/jquery-migrate/jquery-migrate.min.js') }}"></script>
	<script src="{{ asset('public/backend/vendor/popper.js/dist/umd/popper.min.js') }}"></script>
	<script src="{{ asset('public/backend/vendor/bootstrap/bootstrap.min.js') }}"></script>
	<script src="{{ asset('public/backend/vendor/malihu-custom-scrollbar-plugin/jquery.mCustomScrollbar.concat.min.js') }}"></script>
	<script src="{{ asset('public/backend/vendor/toastr/toastr.js') }}"></script>
	<script src="{{ asset('public/backend/vendor/dropify/dropify.min.js') }}"></script>
	<script src="{{ asset('public/backend/js/pace.min.js') }}"></script>
	@if(!Request::is('dashboard'))
	<script src="{{ asset('public/backend/vendor/select2/dist/js/select2.min.js') }}"></script>
	<script src="{{ asset('public/backend/vendor/flatpickr/flatpickr.js') }}"></script>
	<script src="{{ asset('public/backend/vendor/summernote/summernote-bs4.min.js') }}"></script>
	<script src="{{ asset('public/backend/js/jquery.validate.min.js') }}"></script>
	<script src="{{ asset('public/backend/vendor/datatables/jquery.dataTables.min.js') }}"></script>
	<script src="{{ asset('public/backend/vendor/datatables/dataTables.bootstrap4.min.js') }}"></script>
	<script src="{{ asset('public/backend/vendor/datatables/dataTables.responsive.min.js') }}"></script>
	<script src="{{ asset('public/backend/vendor/datatables/responsive.bootstrap4.min.js') }}"></script>
	<script src="{{ asset('public/backend/vendor/bootstrap-datepicker/js/bootstrap-datepicker.js') }}"></script>
	<script src="{{ asset('public/backend/vendor/sweetalert2/sweetalert2.all.min.js') }}"></script>
	@endif
	<script src="{{ asset('public/backend') }}/js/sidebar-nav.js"></script>
	<script src="{{ asset('public/backend') }}/js/main.js"></script>
	<script src="{{ asset('public/backend') }}/js/app.js"></script>
	<script>
		@if( ! Request::is('dashboard'))
		$(".page-title").text($(".card-title").first().text());
		$('title').append(' | ' + $(".card-title").first().text());

		if($('.breadcrumb-box').length > 0){
			$('.breadcrumb-box').html($('.breadcrumb-main').html());
		}else{
			$('.breadcrumb-main').removeClass('d-none');
		}
		@else
		$('title').append(' | ' . $lang_dashboard);
		@endif

		@if(Session::has('success'))
		toast('success', '{{ session('success') }}');
		@endif
		@if(Session::has('error'))
		toast('error', '{{ session('error') }}');
		@endif
		@foreach ($errors->all() as $error)
		toast('error', '{{ $error }}');
		@endforeach
	</script>
	@yield('js-script')
</body>
</html>