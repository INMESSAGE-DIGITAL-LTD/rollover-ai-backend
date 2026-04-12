<form action="{{ route('profile.update') }}" class="ajax-submit" autocomplete="off" enctype="multipart/form-data" method="post">
    @csrf
    <div class="row">
        <div class="col-md-12">
            <div class="form-group">
                <label class="control-label">{{ _lang('First Name') }}</label>
                <input type="text" class="form-control" name="first_name" value="{{ $profile->first_name }}" required>
            </div>
        </div>
        <div class="col-md-12">
            <div class="form-group">
                <label class="control-label">{{ _lang('Last Name') }}</label>
                <input type="text" class="form-control" name="last_name" value="{{ $profile->last_name }}" required>
            </div>
        </div>
        <div class="col-md-12">
            <div class="form-group">
                <label class="control-label">{{ _lang('Email') }}</label>
                <input type="email" class="form-control" name="email" value="{{ $profile->email }}" required>
            </div>
        </div>
        <div class="col-md-12">
            <div class="form-group">
                <label class="control-label">{{ _lang('Image') }}</label>
                <input type="file" class="form-control dropify" name="image" data-allowed-file-extensions="png jpg jpeg PNG JPG JPEG" data-default-file="{{ asset($profile->image) }}">
            </div>
        </div>
        <div class="col-md-12">
            <div class="form-group">
                <button type="submit" class="btn btn-primary btn-sm">{{ _lang('Update') }}</button>
            </div>
        </div>
    </div>
</form>
