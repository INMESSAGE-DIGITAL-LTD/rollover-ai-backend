@extends('layouts.app')

@section('content')
<h4 class="card-title d-none">{{ _lang('Add New') }}</h4>
<form class="ajax-submit2" method="post" autocomplete="off" action="{{ route('live_matches.store') }}" enctype="multipart/form-data">
	@csrf

	<div class="row">
		<div class="col-md-12 mb-2">
			<div class="card">
				<div class="card-body">
					<div class="row">
						<div class="col-md-12">
							<h2 class="b">{{ _lang('Match Information') }}</h2>
						</div>
						<div class="col-md-6">
							<div class="form-group">
								<label class="control-label">{{ _lang('Match Title') }}</label>
								<input type="text" class="form-control" name="match_title" value="{{ old('match_title') }}" required>
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
								<label class="control-label">{{ _lang('Status') }}</label>
								<select class="form-control select2" name="status" required>
									<option value="1">{{ _lang('Active') }}</option>
									<option value="0">{{ _lang('In-Active') }}</option>
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
		<div class="col-md-12 mb-2">
			<div class="card">
				<div class="card-body">
					<div class="row">
						<div class="col-md-12">
							<h2 class="b ml-2">{{ _lang('Sources') }}</h2>
						</div>
						<div class="field-group params-card mx-4 my-2 row" style="width: 100%;">
							<div class="col-md-12 text-right">
								<div class="form-group">
									<button type="button" class="btn btn-danger btn-xs remove-row">-</button>
								</div>
							</div>
							<div class="col-md-6">
								<div class="form-group">
									<label class="form-control-label">{{ _lang('Title') }}</label>
									<input type="text" name="source_title[]" class="form-control" value="" required>
								</div>
							</div>
							<div class="col-md-6">
								<div class="form-group">
									<label class="control-label">{{ _lang('Source Type') }}</label>
									<select class="form-control select2 source_type" name="source_type[]" data-selected="streaming_url" required>
										<option value="streaming_url">{{ _lang('Streaming Url') }}</option>
										<option value="youtube">{{ _lang('Youtube') }}</option>
									</select>
								</div>
							</div>
							<div class="col-md-12 streaming_url">
								<div class="form-group">
									<label class="form-control-label">
										{{ _lang('Streaming Url') }}
									</label>
									<input type="text" name="source_url[]" class="form-control" value="" required>
								</div>
							</div>
							<div class="col-md-6 streaming">
								<div class="form-group">
									<label class="control-label">
										{{ _lang('Source From') }}
										<span class="required"> *</span>
									</label>
									<select class="form-control select2" name="source_from[]" data-selected="default">
										<option value="default">{{ _lang('Default') }}</option>
										<option value="aesport">{{ _lang('AE Sport') }}</option>
										<option value="bingsport">{{ _lang('Bingsport') }}</option>
									</select>
								</div>
							</div>
							
							<div class="col-md-6">
								<div class="form-group">
									<label class="form-control-label">{{ _lang('Status') }}</label>
									<select class="form-control select2" name="source_status[]" data-selected="{{ old('status', 1) }}"  required>
										<option value="1">{{ _lang("Active") }}</option>
										<option value="0">{{ _lang("In-Active") }}</option>
									</select>
								</div>
							</div>
						</div>
						<div class="col-md-12 text-right">
							<div class="form-group">
								<button type="button" class="btn btn-success btn-sm add-more">{{ _lang('Add More Source') }}</button>
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
<div class="d-none">
	<div class="field-group params-card mx-4 my-2 row repeat" style="width: 100%;">
		<div class="col-md-12 text-right">
			<div class="form-group">
				<button type="button" class="btn btn-danger btn-xs remove-row">-</button>
			</div>
		</div>
		<div class="col-md-6">
			<div class="form-group">
				<label class="form-control-label">{{ _lang('Title') }}</label>
				<input type="text" name="source_title[]" class="form-control" value="" required>
			</div>
		</div>
		<div class="col-md-6">
			<div class="form-group">
				<label class="control-label">{{ _lang('Source Type') }}</label>
				<select class="form-control source_type" name="source_type[]" data-selected="streaming_url" required>
					<option value="streaming_url">{{ _lang('Streaming Url') }}</option>
					<option value="youtube">{{ _lang('Youtube') }}</option>
				</select>
			</div>
		</div>
		<div class="col-md-12 streaming_url">
			<div class="form-group">
				<label class="form-control-label">
					{{ _lang('Streaming Url') }}
				</label>
				<input type="text" name="source_url[]" class="form-control" value="" required>
			</div>
		</div>
		<div class="col-md-6 streaming">
								<div class="form-group">
									<label class="control-label">
										{{ _lang('Source From') }}
										<span class="required"> *</span>
									</label>
									<select class="form-control" name="source_from[]" data-selected="default">
										<option value="default">{{ _lang('Default') }}</option>
										<option value="aesport">{{ _lang('AE Sport') }}</option>
										<option value="bingsport">{{ _lang('Bingsport') }}</option>
									</select>
								</div>
							</div>
		<div class="col-md-6">
			<div class="form-group">
				<label class="form-control-label">{{ _lang('Status') }}</label>
				<select class="form-control" name="source_status[]" data-selected="{{ old('status', 1) }}"  required>
					<option value="1">{{ _lang("Active") }}</option>
					<option value="0">{{ _lang("In-Active") }}</option>
				</select>
			</div>
		</div>
	</div>

</div>
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


	$(document).on('click', '.add-more', function(){
		var form = $('.repeat').clone().removeClass('repeat');
		form.find('select').select2();
		$(this).closest('.col-md-12').before(form);
	});
	
	$(document).on('click','.remove-row',function(){
		$(this).closest('.field-group').remove();
	});

	$(document).on('change','.source_type',function(){
		var source_type = $(this).val();
		if(source_type == 'streaming_url'){
			$(this).closest('.field-group')
			.find('.streaming_url')
			.find('label')
			.html('{{ _lang('Streaming Url') }} <span class="required"> *</span>');

			$(this).closest('.field-group').find('.streaming').removeClass('d-none');
		}else{
			$(this).closest('.field-group')
			.find('.streaming_url')
			.find('label')
			.html('{{ _lang('Youtube Url') }} <span class="required"> *</span>');

			$(this).closest('.field-group').find('.streaming').addClass('d-none');
		}
		$(this).closest('.field-group')
		.find('.user_agent')
		.val('default')
		.trigger('change');

		$(this).closest('.field-group')
		.find('.custom_user_agent')
		.addClass('d-none')
		.find('input')
		.val('');

	});
	$(document).on('change','.user_agent',function(){
		var user_agent = $(this).val();
		if(user_agent == 'custom'){
			$(this).closest('.field-group')
			.find('.custom_user_agent')
			.removeClass('d-none');
		}else{
			$(this).closest('.field-group')
			.find('.custom_user_agent')
			.addClass('d-none');
		}
	});
</script>
@endsection


