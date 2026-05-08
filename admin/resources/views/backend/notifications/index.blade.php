@extends('layouts.app')
@section('content')

<div class="row">
    <div class="col-md-6 breadcrumb-box"></div>
    <div class="col-md-6 mb-2 text-right">
        <h2 class="card-title d-none">{{ _lang('Send Notifications List') }}</h2>
        <a class="btn btn-danger btn-sm btn-remove" href="{{ url('notifications/deleteall') }}">
            {{ _lang('Delete All') }}
        </a>
        <a class="btn btn-primary btn-sm" href="{{ route('notifications.create') }}" data-title="{{ _lang('Add New') }}">
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
                            
                            <th style=" white-space: nowrap; ">{{ _lang('Title') }}</th>
                            <th style=" white-space: nowrap; ">{{ _lang('Time') }}</th>

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
<script src="{{ asset('public/backend/js/pages/notifications.js') }}"></script>
@endsection