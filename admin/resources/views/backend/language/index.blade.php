@extends('layouts.app')

@section('content')

<div class="row">
	<div class="col-md-12 mb-2 text-right">
		<h2 class="card-title d-none">{{ _lang('Languages') }}</h2>
		<a class="btn btn-primary btn-sm ajax-modal" href="{{ route('languages.create') }}" title="{{ _lang('Add New') }}">
			<i class="fas fa-plus mr-1"></i>
			{{ _lang('Add New') }}
		</a>
	</div>
	<div class="col-md-12">
		<div class="card">
			<div class="card-body">
				<table class="table table-bordered data-table">
					<thead>
						<tr>
							<th>{{ _lang('Language Name') }}</th>
							<th class="text-center">{{ _lang('Edit Translation') }}</th>
							<th class="text-center no-export">{{ _lang('Remove') }}</th>
						</tr>
					</thead>
					<tbody>
						@foreach(get_language_list() as $language)
						<tr>
							<td>{{ ucwords($language) }}</td>
							<td class="text-center">
								<a href="{{ route('languages.edit', $language) }}" class="btn btn-info btn-xs">
									{{ _lang('Edit Translation') }}
								</a>
							</td>	
							<td class="text-center">
								<form action="{{ route('languages.destroy', $language) }}" method="post" class="ajax-delete">
									@csrf
									@method('DELETE')
									<button class="btn btn-danger btn-xs btn-remove" type="submit">
										{{ _lang('Delete') }}
									</button>
								</form>
							</td>
						</tr>
						@endforeach
					</tbody>
				</table>
			</div>
		</div>
	</div>
</div>

@endsection


