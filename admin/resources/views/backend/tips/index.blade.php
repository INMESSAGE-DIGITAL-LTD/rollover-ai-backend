@extends('layouts.app')

@section('content')

<div class="row">
	<div class="col-md-6 breadcrumb-box"></div>
	<div class="col-md-6 mb-2 text-right">
		<h4 class="card-title d-none">{{ _lang('Tips List') }}</h4>
		<a class="btn btn-primary btn-sm" href="{{ route('tips.create') }}" data-title="{{ _lang('Add New') }}">
			<i class="fas fa-plus mr-1"></i>
			{{ _lang('Add New') }}
		</a>
	</div>
	<div class="col-md-12">
		<div class="card">
			<div class="card-body">
				<table class="table table-bordered" id="data-table">
					<thead>
						<tr>
							
        					<th style=" white-space: nowrap; ">{{ _lang('Team One') }}</th>
							<th style=" white-space: nowrap; ">{{ _lang('Team Two') }}</th>
							<th style=" white-space: nowrap; width: 25%;">{{ _lang('Title & Time') }}</th>

        					<th>{{ _lang('Result') }}</th>
        					<th>{{ _lang('Status') }}</th>

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
		ajax: _url + "/tips",
		"columns" : [
			
        	{ data : "team_one", name : "team_one", className: 'details-control', responsivePriority: 1 },
		{ data : "team_two", name : "team_two", className : "team_two" },
		{ data : "match_time", name : "match_time", className : "match_time text-center" },
		{ data : "result", name : "result", className : "result" },
        	{ data : "status", name : "status", className : "status" },
			{ data : "action", name : "action", orderable : false, searchable : false, className : "text-center" }
			
		],
		responsive: true,
		"bStateSave": true,
		"bAutoWidth":false,	
		"ordering": false
	});
</script>
@endsection