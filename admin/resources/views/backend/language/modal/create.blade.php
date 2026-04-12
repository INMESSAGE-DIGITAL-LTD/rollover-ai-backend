<form action="{{ route('languages.store') }}" class="ajax-submit" autocomplete="off" method="post">
    @csrf
    <div class="row">
        <div class="col-md-12">
            <div class="form-group">
                <label class="control-label">{{ _lang('Language Name') }}</label>
                <input type="text" class="form-control" name="language_name" value="{{ old('language_name') }}" required>
            </div>
        </div>
        <div class="col-md-12">
            <div class="form-group">
                <button type="reset" class="btn btn-danger">{{ _lang('Reset') }}</button>
                <button type="submit" class="btn btn-primary">{{ _lang('Save') }}</button>
            </div>
        </div>
    </div>
</form>

