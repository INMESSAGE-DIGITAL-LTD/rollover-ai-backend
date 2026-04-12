@extends('layouts.app')

@section('content')
<div class="card-title d-none">{{ _lang('Details') }}</div>
<div class="row">
    <div class="col-md-6">
        <div class="card">
            <div class="card-body">
                <table class="table table-bordered">
                    <tbody>
                        <tr>
                            <td colspan="2" class="text-center">
                                <img src="{{ asset($profile->image) }}" class="img-lg img-thumbnail">
                            </td>
                        </tr>
                        <tr>
                            <td>{{ _lang('Name') }}</td>
                            <td>{{ $profile->name }}</td>
                        </tr>
                        <tr>
                            <td>{{ _lang('Email') }}</td>
                            <td>{{ $profile->email }}</td>
                        </tr>
                        <tr>
                            <td>{{ _lang('Status') }}</td>
                            <td>
                                @if($profile->status)
                                <span class="badge badge-success">{{ _lang('Active') }}</span>
                                @else
                                <span class="badge badge-danger">{{ _lang('In-Active') }}</span>
                                @endif
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>
@endsection
