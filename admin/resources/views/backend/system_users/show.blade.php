@extends('layouts.app')

@section('content')
<h2 class="card-title d-none">{{ _lang('Details') }}</h2>
<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-body">
                <table class="table table-bordered">

                    <tr>
                        <td colspan="2" class="text-center">
                            <img src="{{ asset($user->image) }}" class="img-lg img-thumbnail">
                        </td>
                    </tr>
                    <tr>
                        <td>{{ _lang('Name') }}</td>
                        <td>{{ $user->name }}</td>
                    </tr>
                    <tr>
                        <td>{{ _lang('Email') }}</td>
                        <td>{{ $user->email }}</td>
                    </tr>
                    <tr>
                        <td>{{ _lang('User Type') }}</td>
                        <td>{{ ucwords(str_replace('_', ' ', $user->user_type)) }}</td>
                    </tr>
                    <tr>
                        <td>{{ _lang('Apps') }}</td>
                        <td>
                            @if($user->user_type == 'moderator')
                                @php
                                    $apps_name = '';
                                    $apps_ids = json_decode($user->apps) ?? [];

                                    foreach (\App\Models\AppModel::whereIn('id', $apps_ids)->get() as $key => $app){
                                        $apps_name .= $app->app_name . ', ';
                                    }

                                    echo $apps_name;
                                @endphp
                            @else
                                All Apps
                            @endif
                        </td>
                    </tr>
                    <tr>
                        <td>{{ _lang('Status') }}</td>
                        <td>
                            @if($user->status)
                            <span class="badge badge-success">{{ _lang('Active') }}</span>
                            @else
                            <span class="badge badge-danger">{{ _lang('In-Active') }}</span>
                            @endif
                        </td>
                    </tr>

                </table>
            </div>
        </div>
    </div>
</div>
@endsection

