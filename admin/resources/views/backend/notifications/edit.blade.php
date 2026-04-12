@extends('layouts.app')

@section('content')
<h2 class="card-title d-none">{{ _lang('Send Notification') }}</h2>
<div class="row">
    <div class="col-md-12">
        <div class="card">
            <div class="card-body">
               <form method="post" class="ajax-submit2sss" autocomplete="off" action="{{ route('notifications.store') }}" enctype="multipart/form-data">
                    @csrf
                    <div class="row">
                        
                        <div class="col-md-12">
                            <div class="form-group">
                                <label class="control-label">{{ _lang('Title') }}</label>
                                <input type="text" class="form-control" name="title" value="{{ $notification->title }}" required>
                            </div>
                        </div>
                        <div class="col-md-12">
                            <div class="form-group">
                                <label class="control-label">{{ _lang('Body') }}</label>
                                <textarea rows="4"  class="form-control" name="body" required>{{ $notification->message }}</textarea>
                            </div>
                        </div>
                        <div class="col-md-12">
                            <div class="form-group">
                                <label class="control-label">{{ _lang('Image Type') }}</label>
                                <select class="form-control select2" name="image_type" data-selected="{{ $notification->image_type }}">
                                    <option value="none">{{ _lang('None') }}</option>
                                    <option value="url">{{ _lang('Url') }}</option>
                                    <option value="image">{{ _lang('Image') }}</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-12 d-none">
                            <div class="form-group">
                                <label class="control-label">{{ _lang('Image Url') }}</label>
                                <input type="text" class="form-control" name="image_url" value="{{ $notification->image_url }}" >
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="form-group image">

                            </div>
                        </div>

                        <div class="col-md-12 d-none">
                            <div class="form-group">
                                <label class="control-label">{{ _lang('Image') }}</label>
                                <input type="file" class="form-control dropify" name="image" data-allowed-file-extensions="png jpg jpeg PNG JPG JPEG"data-default-file="{{ $notification->image ? asset($notification->image) : '' }}">
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="form-group image">
                                @if ($notification->image_type == 'url')
                                    <img src="{{ $notification->image_url }}" style="width: 150px; border-radius: 10px;">
                                @endif
                            </div>
                        </div>
                        <div class="col-md-12">
                            <div class="form-group">
                                <label class="control-label">{{ _lang('Action Url') }}</label>
                                <input type="text" class="form-control" name="action_url" value="{{ $notification->action_url }}" >
                            </div>
                        </div>


                        <div class="col-md-12">
                            <div class="form-group">
                                <button type="submit" class="btn btn-primary btn-sm">{{ _lang('Send') }}</button>
                            </div>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
@endsection


@section('js-script')
<script type="text/javascript">

    @if ($notification->image_type == 'image')
    $('[name=image]').closest('.col-md-12').removeClass('d-none');
    @elseif ($notification->image_type == 'url')
    $('[name=image_url]').parent().parent().removeClass('d-none');
    @else
    $('[name=image]').closest('.col-md-12').addClass('d-none');
    $('[name=image_url]').parent().parent().addClass('d-none');
    @endif
    $('[name=image_type]').on('change', function() {
        $('[name=image]').closest('.col-md-12').addClass('d-none');
        $('[name=image_url]').parent().parent().addClass('d-none');
        
        if($(this).val() == 'url'){
            $('[name=image_url]').parent().parent().removeClass('d-none');
            $('.image img').show();
            
        }else if($(this).val() == 'image'){
            $('.image img').hide();
            $('[name=image]').closest('.col-md-12').removeClass('d-none');
        }else{
            $('.image img').hide();
            $('[name=image]').closest('.col-md-12').addClass('d-none');
            $('[name=image_url]').parent().parent().addClass('d-none');
        }
    });

    $('[name=image_url]').on('keyup', function() {
        $('.image').html('<img src="' + $(this).val() + '" style="width: 150px; border-radius: 10px;">');
    });
</script>
@endsection
