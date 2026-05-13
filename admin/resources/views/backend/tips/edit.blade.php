@extends('layouts.app')

@section('content')
<h4 class="card-title d-none">{{ _lang('Edit') }}</h4>
<form class="ajax-submit2" method="post" autocomplete="off" action="{{ route('tips.update', $tip->id) }}" enctype="multipart/form-data">
	@csrf
	@method('PUT')
	<div class="row">
		<div class="col-md-12 mb-2">
			<div class="card">
				<div class="card-body">

					<div class="row">
						
						<div class="col-md-6">
							<div class="form-group">
								<label class="form-control-label">{{ _lang('Title') }}</label>
								<input type="text" name="title" class="form-control" value="{{ $tip->title }}" required>
							</div>
						</div>
						<div class="col-md-6">
							<div class="form-group">
								<label class="form-control-label">{{ _lang('League') }}</label>
								<select class="form-control select2" name="league" data-selected="{{ $tip->league }}"  required>
									<option value="">Select One</option>
									@foreach(get_leagues() AS $league)
									<option value="{{ $league->league->name }}">{{ $league->league->name }}</option>
									@endforeach
								</select>
							</div>
						</div>
						
						<div class="col-md-6">
							<div class="form-group">
								<label class="form-control-label">{{ _lang('Odds Value') }}</label>
								<input type="number" name="odds_number" class="form-control" value="{{ $tip->odds_number }}" required>
							</div>
						</div>
						<div class="col-md-6">
							<div class="form-group">
								<label class="form-control-label">{{ _lang('Odds Text') }}</label>
								<input type="text" name="odds_value" class="form-control" value="{{ $tip->odds_value }}" required>
							</div>
						</div>
						<div class="col-md-6">
							<div class="form-group">
								<label class="control-label">{{ _lang('Match Time') }}</label>
								<input type="text" class="form-control flatpickr" name="match_time" value="{{ $tip->match_time2 }}" required>
							</div>
						</div>
						<div class="col-md-6">
							<div class="form-group">
								<label class="form-control-label">{{ _lang('Result') }}</label>
								
								<select class="form-control select2" name="result" data-selected="{{ $tip->result }}"  required>
									<option value="pending">{{ _lang("Pending") }}</option>
									<option value="win">{{ _lang("Win") }}</option>
									<option value="loss">{{ _lang("Loss") }}</option>
								</select>
							</div>
						</div>
						<div class="col-md-6">
							<div class="form-group">
								<label class="form-control-label">{{ _lang('Bet Link') }}</label>
								<input type="text" name="bet_link" class="form-control" value="{{ $tip->bet_link }}">
							</div>
						</div>
						<div class="col-md-6">
							<div class="form-group">
								<label class="form-control-label">{{ _lang('Status') }}</label>
								<select class="form-control select2" name="status" data-selected="{{ $tip->status }}"  required>
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
                                <input type="text" class="form-control" name="team_one_name" value="{{ $tip->team_one_name }}"  required>
                            </div>
                        </div>
                        <div class="col-md-12">
                            <div class="form-group">
                                <label class="control-label">{{ _lang('Image Type') }}</label>
                                <select class="form-control select2" name="team_one_image_type" data-selected="{{ $tip->team_one_image_type }}">
                                    <option value="none">{{ _lang('None') }}</option>
                                    <option value="url">{{ _lang('Url') }}</option>
                                    <option value="image">{{ _lang('Image') }}</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-12 d-none">
                            <div class="form-group">
                                <label class="control-label">{{ _lang('Image Url') }}</label>
                                <input type="text" class="form-control" name="team_one_url" value="{{ $tip->team_one_url }}" >
                            </div>
                        </div>
                        <div class="col-md-12 d-none">
                            <div class="form-group">
                                <label class="control-label">{{ _lang('Image') }}</label>
                                <input type="file" class="form-control dropify" name="team_one_image" data-allowed-file-extensions="png jpg jpeg PNG JPG JPEG"data-default-file="{{ $tip->team_one_image ? asset($tip->team_one_image) : '' }}">
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="form-group team_one_image">
                                @if($tip->team_one_image_type == 'url')
                                <img src="{{ $tip->team_one_url }}" style="width: 150px; border-radius: 10px;">
                                @endif
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
                                <input type="text" class="form-control" name="team_two_name" value="{{ $tip->team_two_name }}"  required>
                            </div>
                        </div>
                        <div class="col-md-12">
                            <div class="form-group">
                                <label class="control-label">{{ _lang('Image Type') }}</label>
                                <select class="form-control select2" name="team_two_image_type" data-selected="{{ $tip->team_two_image_type }}">
                                    <option value="none">{{ _lang('None') }}</option>
                                    <option value="url">{{ _lang('Url') }}</option>
                                    <option value="image">{{ _lang('Image') }}</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-12 d-none">
                            <div class="form-group">
                                <label class="control-label">{{ _lang('Image Url') }}</label>
                                <input type="text" class="form-control" name="team_two_url" value="{{ $tip->team_two_url }}" >
                            </div>
                        </div>
                        <div class="col-md-12 d-none">
                            <div class="form-group">
                                <label class="control-label">{{ _lang('Image') }}</label>
                                <input type="file" class="form-control dropify" name="team_two_image" data-allowed-file-extensions="png jpg jpeg PNG JPG JPEG" data-default-file="{{ $tip->team_two_image ? asset($tip->team_two_image) : '' }}">
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="form-group team_two_image">
                                @if($tip->team_two_image_type == 'url')
                                <img src="{{ $tip->team_two_url }}" style="width: 150px; border-radius: 10px;">
                                @endif
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
	@if($tip->team_one_image_type == 'url')
    $('[name=team_one_url]').parent().parent().removeClass('d-none');
    @elseif($tip->team_one_image_type == 'image')
    $('[name=team_one_image]').closest('.col-md-12').removeClass('d-none');
    @else
    $('[name=team_one_image]').closest('.col-md-12').addClass('d-none');
    $('[name=team_one_url]').parent().parent().addClass('d-none');
    @endif

    @if($tip->team_two_image_type == 'url')
    $('[name=team_two_url]').parent().parent().removeClass('d-none');
    @elseif($tip->team_two_image_type == 'image')
    $('[name=team_two_image]').closest('.col-md-12').removeClass('d-none');
    @else
    $('[name=team_two_image]').closest('.col-md-12').addClass('d-none');
    $('[name=team_two_url]').parent().parent().addClass('d-none');
    @endif

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
        var $this = $(this);
        var val = $this.val().trim();
    
        if (val.includes('sofascore')) {
            $('.team_one_image').html('<div class="team_one_loader">Uploading...</div>');
            updateLogo('[name=team_one_url]', function(newUrl) {
                $('.team_one_image').html('<img src="' + newUrl + '" style="width: 150px; border-radius: 10px;">');
            });
        } else {
            $('.team_one_image').html('<img src="' + val + '" style="width: 150px; border-radius: 10px;">');
        }
    });
    
    $('[name=team_two_url]').on('keyup', function() {
        var $this = $(this);
        var val = $this.val().trim();
    
        if (val.includes('sofascore')) {
            $('.team_two_image').html('<div class="team_one_loader">Uploading...</div>');
            updateLogo('[name=team_two_url]', function(newUrl) {
                $('.team_two_image').html('<img src="' + newUrl + '" style="width: 150px; border-radius: 10px;">');
            });
        } else {
            $('.team_two_image').html('<img src="' + val + '" style="width: 150px; border-radius: 10px;">');
        }
    });
	
	
	function updateLogo(selector, callback) {
        const $input = $(selector);
        const $previewImage = $('<img style="display:none;" crossorigin="anonymous" />').appendTo('body');
    
        const imageUrl = $input.val().trim();
        
        console.log("imageUrl", imageUrl);
    
            const match = imageUrl.match(/team\/(\d+)\/image$/);
            if (!match) return;
    
            const teamId = match[1];
            const fileName = `${teamId}.png`;
    
            $previewImage.attr('src', imageUrl);
    
            $previewImage.off('load').on('load', function () {
                const canvas = document.createElement('canvas');
                canvas.width = this.naturalWidth;
                canvas.height = this.naturalHeight;
    
                const ctx = canvas.getContext('2d');
                ctx.drawImage(this, 0, 0);
    
                canvas.toBlob(function(blob) {
                    const formData = new FormData();
                    const file = new File([blob], fileName, { type: 'image/png' });
                    formData.append('image', file);
                    formData.append('filename', fileName);
    
                    $.ajax({
                        url: 'https://realtips.inmessage.xyz/api/v1/upload-logo',
                        type: 'POST',
                        data: formData,
                        contentType: false,
                        processData: false,
                        success: function (response) {
                            
                            console.log('Upload', response);
                            if (response.status && response.image) {
                                $input.val(response.image);
                                if (typeof callback === 'function') {
                                    callback(response.image);
                                }
                            } else {
                                console.warn('Upload failed:', response);
                            }
                        },
                        error: function (xhr) {
                            console.error('Upload error', xhr);
                        }
                    });
                }, 'image/png');
            });
    
            $previewImage.off('error').on('error', function () {
                console.warn('Failed to load image:', imageUrl);
            });
    }
</script>
@endsection

