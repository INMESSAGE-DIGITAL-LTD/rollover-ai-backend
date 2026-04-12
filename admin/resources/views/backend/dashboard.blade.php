@extends('layouts.app')

@section('content')
<div class="row">
	<div class="col-sm-6 col-xl-3 mb-4">
		<div class="card">
			<div class="card-body media align-items-center px-xl-3">
				<div class="u-doughnut u-doughnut--70 mr-3 mr-xl-2">
					<canvas class="js-doughnut-chart" width="70" height="70"
					data-set="[100, 0]"
					data-colors='[
					"#2972fa",
					"#f6f9fc"
					]'></canvas>

					<div class="u-doughnut__label text-info">
						<i class="fa fa-tv"></i>
					</div>
				</div>

				<div class="media-body">
					
					<span class="h2 mb-0">{{ counter('live_matches', ['status' => 1]) }}</span>
					<h5 class="h6 text-muted text-uppercase mb-2">
						Live Matches
					</h5>
				</div>
			</div>
		</div>
	</div>

	<div class="col-sm-6 col-xl-3 mb-4">
		<div class="card">
			<div class="card-body media align-items-center px-xl-3">
				<div class="u-doughnut u-doughnut--70 mr-3 mr-xl-2">
					<canvas class="js-doughnut-chart" width="70" height="70"
					data-set="[100, 0]"
					data-colors='[
					"#fab633",
					"#f6f9fc"
					]'></canvas>

					<div class="u-doughnut__label text-warning">
						<i class="fa fa-users"></i>
					</div>
				</div>

				<div class="media-body">
					
					<span class="h2 mb-0">{{ counter('users', ['status' => 1, 'user_type' => 'user']) }}</span>
					<h5 class="h6 text-muted text-uppercase mb-2">
						Users
					</h5>
				</div>
			</div>
		</div>
	</div>

	<div class="col-sm-6 col-xl-3 mb-4">
		<div class="card">
			<div class="card-body media align-items-center px-xl-3">
				<div class="u-doughnut u-doughnut--70 mr-3 mr-xl-2">
					<canvas class="js-doughnut-chart" width="70" height="70"
					data-set="[100, 0]"
					data-colors='[
					"#0dd157",
					"#f6f9fc"
					]'></canvas>

					<div class="u-doughnut__label text-success">
						<i class="fa fa-cubes"></i>
					</div>
				</div>

				<div class="media-body">
					
					<span class="h2 mb-0">{{ counter('tips', ['status' => 1]) }}</span>
					<h5 class="h6 text-muted text-uppercase mb-2">
						Tips
					</h5>
				</div>
			</div>
		</div>
	</div>

	<div class="col-sm-6 col-xl-3 mb-4">
		<div class="card">
			<div class="card-body media align-items-center px-xl-3">
				<div class="u-doughnut u-doughnut--70 mr-3 mr-xl-2">
					<canvas class="js-doughnut-chart" width="70" height="70"
					data-set="[100, 0]"
					data-colors='[
					"#fb4143"
					]'></canvas>

					<div class="u-doughnut__label text-danger">
						<i class="fa fa-image"></i></div>
					</div>

				<div class="media-body">
					
					<span class="h2 mb-0">{{ counter('subscriptions', ['status' => 1]) }}</span>
					<h5 class="h6 text-muted text-uppercase mb-2">
						subscriptions
					</h5>
				</div>
			</div>
		</div>
	</div>
</div>
<!-- End Doughnut Chart -->

@endsection

@section('js-script')
<script src="{{ asset('public/backend') }}/vendor/chart.js/dist/Chart.min.js"></script>
<script src="{{ asset('public/backend') }}/js/dashboard-page-scripts.js"></script>
@endsection