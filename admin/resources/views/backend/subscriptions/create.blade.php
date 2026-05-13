@extends('layouts.app')

@section('content')
    <style>
        .d-wrapper .dropify-wrapper {
            height: 100px;
        }
    </style>
    <h2 class="card-title d-none">{{ _lang('Add New') }}</h2>
    <form class="ajax-submit2" method="post" autocomplete="off" action="{{ route('subscriptions.store') }}"
        enctype="multipart/form-data">
        @csrf
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-12">
                                <h2 class="b">Information</h2>
                            </div>
                            <div class="col-md-12">
                                <div class="form-group">
                                    <label class="control-label">{{ _lang('Name') }}</label>
                                    <input type="text" class="form-control" name="name" value="{{ old('name') }}"
                                        required>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="form-group">
                                    <label class="control-label">{{ _lang('Duration Type') }}</label>
                                    <select class="form-control select2" name="duration_type"
                                        data-selected="{{ old('duration_type', 'day') }}" required>
                                        <option value="day">{{ _lang('Daily') }}</option>
                                        <option value="month">{{ _lang('Monthly') }}</option>
                                        <option value="year">{{ _lang('Yearly') }}</option>
                                    </select>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="form-group">
                                    <label class="control-label">{{ _lang('Duration') }}</label>
                                    <input type="number" class="form-control" name="duration"
                                        value="{{ old('duration', 1) }}" required>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="form-group">
                                    <label class="control-label">{{ _lang('Platform') }}</label>
                                    <select class="form-control select2" name="platform"
                                        data-selected="{{ old('platform') }}" required>
                                        <option value="">{{ _lang('Select One') }}</option>
                                        <option value="android">{{ _lang('Android') }}</option>
                                        <option value="ios">{{ _lang('IOS') }}</option>
                                    </select>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="form-group">
                                    <label class="control-label">{{ _lang('Product Id') }}</label>
                                    <input type="text" class="form-control" name="product_id" value="{{ old('product_id') }}" required>
                                </div>
                            </div>
                            <div class="col-md-12">
                                <div class="form-group">
                                    <label class="control-label">{{ _lang('Status') }}</label>
                                    <select class="form-control select2" name="status" required>
                                        <option value="1">{{ _lang('Active') }}</option>
                                        <option value="0">{{ _lang('In-Active') }}</option>
                                    </select>
                                </div>
                            </div>

                            <div class="col-md-12">
                                <div class="form-group">
                                    <button type="reset" class="btn btn-danger btn-sm">{{ _lang('Reset') }}</button>
                                    <button type="submit" class="btn btn-primary btn-sm">{{ _lang('Save') }}</button>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <div class="card">
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-12">
                                <h2 class="b">Description</h2>
                            </div>
                            <div class="col-md-12">
                                <div class="row field_group my-2">
                                    <div class="col-md-12">
                                        <div class="form-group text-right">
                                            <button class="btn btn-danger remove-row btn-sm text-white mt-1">-</button>
                                        </div>
                                    </div>
                                    <div class="col-md-12">
                                        <div class="form-group">
                                            <label class="control-label">Description</label>
                                            <input type="text" class="form-control" name="description[]" value=""
                                                required="">
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-12 ml-1">
                                <div class="form-group text-right">
                                    <button type="button" class="btn btn-primary add-more btn-sm" data-team="LR56SVES0">
                                        Add New
                                    </button>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            </div>
        </div>
    </form>

    <div class="d-none">
        <div class="field_group repeat col-md-12">
            <div class="row my-2">
                <div class="col-md-12">
                    <div class="form-group text-right">
                        <button class="btn btn-danger remove-row btn-sm text-white mt-1">-</button>
                    </div>
                </div>
                <div class="col-md-12">
                    <div class="form-group">
                        <label class="control-label">Description</label>
                        <input type="text" class="form-control" name="description[]" value="" required="">
                    </div>
                </div>
            </div>
        </div>
    </div>
@endsection

@section('js-script')
<script type="text/javascript">

    $(document).on('click', '.add-more', function() {
        var form = $('.repeat').clone().removeClass('repeat');
        form.find('.image').dropify();
        $(this).closest('.col-md-12').before(form);
    });

    $(document).on('click', '.remove-row', function() {
        $(this).closest('.field_group').remove();
    });
</script>
@endsection
