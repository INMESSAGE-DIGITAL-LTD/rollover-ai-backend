@extends('layouts.app')
@section('content')
<div class="card-title d-none">{{ _lang('Add New') }}</div>
<div class="row">
	<div class="col-md-6">
		<div class="card" >
			<div class="card-body">
				<form action="{{ route('languages.store') }}" class="validate" autocomplete="off" method="post">
					@csrf
					<div class="col-md-12">
						<div class="form-group">
							<label class="control-label">{{ _lang('Language Name') }}</label>
							<input type="text" class="form-control" name="language_name" value="{{ old('language_name') }}" required>
						</div>
					</div>
					<div class="col-md-12">
						<div class="form-group text-right">
							<button type="submit" class="btn btn-primary">{{ _lang('Create') }}</button>
						</div>
					</div>
				</form>	
			</div>
		</div>
	</div>
</div>
@endsection