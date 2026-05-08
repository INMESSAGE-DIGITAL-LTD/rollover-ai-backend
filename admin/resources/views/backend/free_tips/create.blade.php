@extends('layouts.app')

@section('content')

<h4 class="card-title d-none">{{ _lang('Add New') }}</h4>
<form class="ajax-submit2" method="post" autocomplete="off" action="{{ route('free_tips.store') }}" enctype="multipart/form-data">
	@csrf
	<div class="row">
		<div class="col-md-12 mb-2">
			<div class="card">
				<div class="card-body">

					<div class="row">
						
						<div class="col-md-6">
							<div class="form-group">
								<label class="form-control-label">{{ _lang('Title') }}</label>
								<input type="text" name="title" class="form-control" value="{{ old('title') }}" required>
							</div>
						</div>
						<div class="col-md-6">
							<div class="form-group">
								<label class="form-control-label">{{ _lang('League') }}</label>
								<select class="form-control select2" name="league" data-selected="{{ old('league', '') }}"  required>
									<option value="">Select One</option>
									@foreach(get_leagues() AS $league)
									<option value="{{ $league->league->name }}">{{ $league->league->name }}</option>
									@endforeach
								</select>
							</div>
						</div>
						<div class="col-md-6">
							<div class="form-group">
								<label class="control-label">{{ _lang('Match Time') }}</label>
								<input type="text" class="form-control flatpickr" name="match_time" value="{{ old('match_time') }}" required>
							</div>
						</div>
						<div class="col-md-6">
							<div class="form-group">
								<label class="form-control-label">{{ _lang('Odds Value') }}</label>
								<input type="text" name="odds_value" class="form-control" value="{{ old('odds_value') }}" required>
							</div>
						</div>
						<div class="col-md-6">
							<div class="form-group">
								<label class="form-control-label">{{ _lang('Result') }}</label>
								
								<select class="form-control select2" name="result" data-selected="{{ old('result', 'pending') }}"  required>
									<option value="pending">{{ _lang("Pending") }}</option>
									<option value="win">{{ _lang("Win") }}</option>
									<option value="loss">{{ _lang("Loss") }}</option>
								</select>
							</div>
						</div>
						<div class="col-md-6">
							<div class="form-group">
								<label class="form-control-label">{{ _lang('Bet Link') }}</label>
								<input type="text" name="bet_link" class="form-control" value="{{ old('bet_link', '') }}">
							</div>
						</div>
						<div class="col-md-6">
							<div class="form-group">
								<label class="form-control-label">{{ _lang('Status') }}</label>
								<select class="form-control select2" name="status" data-selected="{{ old('status', 1) }}"  required>
									<option value="1">{{ _lang("Active") }}</option>
									<option value="0">{{ _lang("In-Active") }}</option>
								</select>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="col-md-6 mb-2">
			<div class="card">
				<div class="card-body">
					<div class="row">

						<div class="col-md-12">
							<h2 class="b">{{ _lang('Team One Information') }}</h2>
						</div>
						

						<div class="col-md-12">
							<div class="form-group">
								<label class="control-label">{{ _lang('Name') }}</label>
								<input type="text" class="form-control" name="team_one_name" value="{{ old('team_one_name') }}"  required>
							</div>
						</div>
						<div class="col-md-12">
							<div class="form-group">
								<label class="control-label">{{ _lang('Image Type') }}</label>
								<select class="form-control select2" name="team_one_image_type" data-selected="{{ old('team_one_image_type', 'none') }}">
									<option value="none">{{ _lang('None') }}</option>
									<option value="url">{{ _lang('Url') }}</option>
									<option value="image">{{ _lang('Image') }}</option>
								</select>
							</div>
						</div>
						<div class="col-md-12 d-none">
							<div class="form-group">
								<label class="control-label">{{ _lang('Image Url') }}</label>
								<input type="text" class="form-control" name="team_one_url" value="{{ old('team_one_url') }}" >
							</div>
						</div>
						<div class="col-md-12 d-none">
							<div class="form-group">
								<label class="control-label">{{ _lang('Image') }}</label>
								<input type="file" class="form-control dropify" name="team_one_image" data-allowed-file-extensions="png jpg jpeg PNG JPG JPEG">
							</div>
						</div>
						<div class="col-md-4">
							<div class="form-group team_one_image">

							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="col-md-6 mb-2">
			<div class="card">
				<div class="card-body">
					<div class="row">
						<div class="col-md-12">
							<h2 class="b">{{ _lang('Team Two Information') }}</h2>
						</div>
						<div class="col-md-12">
							<div class="form-group">
								<label class="control-label">{{ _lang('Name') }}</label>
								<input type="text" class="form-control" name="team_two_name" value="{{ old('team_two_name') }}" required>
							</div>
						</div>
						<div class="col-md-12">
							<div class="form-group">
								<label class="control-label">{{ _lang('Image Type') }}</label>
								<select class="form-control select2" name="team_two_image_type" data-selected="{{ old('team_two_image_type', 'none') }}">
									<option value="none">{{ _lang('None') }}</option>
									<option value="url">{{ _lang('Url') }}</option>
									<option value="image">{{ _lang('Image') }}</option>
								</select>
							</div>
						</div>
						<div class="col-md-12 d-none">
							<div class="form-group">
								<label class="control-label">{{ _lang('Image Url') }}</label>
								<input type="text" class="form-control" name="team_two_url" value="{{ old('team_two_url') }}" >
							</div>
						</div>
						<div class="col-md-12 d-none">
							<div class="form-group">
								<label class="control-label">{{ _lang('Image') }}</label>
								<input type="file" class="form-control dropify" name="team_two_image" data-allowed-file-extensions="png jpg jpeg PNG JPG JPEG">
							</div>
						</div>
						<div class="col-md-4">
							<div class="form-group team_two_image">

							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
		<div class="col-md-12">
			<div class="card">
				<div class="card-body">
					<div class="row text-right">
						<div class="col-md-12">
							<button type="reset" class="btn btn-danger btn-sm">{{ _lang('Reset') }}</button>
							<button type="submit" class="btn btn-primary btn-sm">{{ _lang('Save') }}</button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</form>
@endsection



@section('js-script')
<script type="text/javascript">
	$('[name=team_one_image_type]').on('change', function() {
		$('[name=team_one_image]').closest('.col-md-12').addClass('d-none');
		$('[name=team_one_url]').parent().parent().addClass('d-none');
		
		if($(this).val() == 'url'){
			$('[name=team_one_url]').parent().parent().removeClass('d-none');
			
		}else if($(this).val() == 'image'){
			$('[name=team_one_image]').closest('.col-md-12').removeClass('d-none');
		}else{
			$('[name=team_one_image]').closest('.col-md-12').addClass('d-none');
			$('[name=team_one_url]').parent().parent().addClass('d-none');
		}
	});
	$('[name=team_two_image_type]').on('change', function() {
		$('[name=team_two_image]').closest('.col-md-12').addClass('d-none');
		$('[name=team_two_url]').parent().parent().addClass('d-none');
		
		if($(this).val() == 'url'){
			$('[name=team_two_url]').parent().parent().removeClass('d-none');
			
		}else if($(this).val() == 'image'){
			$('[name=team_two_image]').closest('.col-md-12').removeClass('d-none');
		}else{
			$('[name=team_two_image]').closest('.col-md-12').addClass('d-none');
			$('[name=team_two_url]').parent().parent().addClass('d-none');
		}
		
	});

	$('[name=team_one_url]').on('keyup', function() {
		$('.team_one_image').html('<img src="' + $(this).val() + '" style="width: 150px; border-radius: 10px;">');
	});
	$('[name=team_two_url]').on('keyup', function() {
		$('.team_two_image').html('<img src="' + $(this).val() + '" style="width: 150px; border-radius: 10px;">');
	});
</script>
@endsection