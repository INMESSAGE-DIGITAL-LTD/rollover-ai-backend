@extends('layouts.app')

@section('content')

<div class="row">
	<div class="col-md-6 breadcrumb-box"></div>
	<div class="col-md-6 mb-2 text-right">
		<h2 class="card-title d-none">{{ _lang('Payments List') }}</h2>
	</div>
	<div class="col-md-12">
		<div class="card">
			<div class="card-body">
				<table class="table table-bordered" id="data-table">
					<thead>
						<tr>
								<th>{{ _lang('User') }}</th>
								<th>{{ _lang('Subscription') }}</th>
								<th>{{ _lang('Amount') }}</th>
								<th>{{ _lang('Platform') }}</th>
								<th class="text-center">{{ _lang('Action') }}</th>
						</tr>
					</thead>
				</table>
			</div>
		</div>
	</div>
</div>

@endsection

@section('js-script')
<script type="text/javascript">
	$('#data-table').DataTable({
		processing: true,
		serverSide: true,
		ajax: _url + "/payments",
		"columns" : [
			
        	{ data : "name", name : "name", className : "name" },
        	{ data : "subscription.name", name : "subscription.name", className : "name" },
        	{ data : "amount", name : "amount", className : "amount" },
        	{ data : "platform", name : "platform", className : "platform" },
					{ data : "action", name : "action", orderable : false, searchable : false, className : "text-center" }
			
		],
		responsive: true,
		"bStateSave": true,
		"bAutoWidth":false,	
		"ordering": false
	});
</script>
@endsection