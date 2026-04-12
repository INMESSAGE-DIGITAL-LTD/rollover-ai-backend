@extends('layouts.app')
@section('content')
<div class="card-title" style="display: none;">{{ _lang('App Settings') }}</div>
<div class="row">
    <div class="col-md-3">
        <div class="nav flex-column nav-pills nav-primary nav-pills-no-bd" id="v-pills-tab-without-border" role="tablist" aria-orientation="vertical">
            <a class="nav-link active show" id="v-pills-links-tab" data-toggle="pill" href="#v-pills-links" role="tab" aria-controls="v-pills-email" aria-selected="true">{{ _lang('General Settings') }}</a>
            <a class="nav-link" id="v-pills-android-tab" data-toggle="pill" href="#v-pills-android" role="tab" aria-controls="v-pills-android" aria-selected="false">{{ _lang('Android Settings') }}</a>
            <a class="nav-link" id="v-pills-ios-tab" data-toggle="pill" href="#v-pills-ios" role="tab" aria-controls="v-pills-ios" aria-selected="false">{{ _lang('IOS Settings') }}</a>
            
        </div>
    </div>
    <div class="col-md-9">
        <div class="tab-content" id="v-pills-without-border-tabContent">
            <div class="tab-pane fade active show" id="v-pills-links" role="tabpanel" aria-labelledby="v-pills-live-tab">
                <div class="card">
                    <div class="card-body">
                        <h3 class="mb-3 header-title card-title">{{ _lang('General') }}</h3>
                        <form method="post" class="ajax-submit2 params-card" autocomplete="off" action="{{ route('store_settings') }}">
                            @csrf
                            <div class="row">
                                <div class="col-md-12">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Api Key') }}</label>
                                        <input type="text" class="form-control" value="{{ env('X_API_KEY') }}" disabled required>
                                    </div>
                                </div>
                            </div>
                        </form>
                        <h3 class="mb-3 mt-3 header-title card-title">{{ _lang('Links') }}</h3>
                        <form method="post" class="ajax-submit2 params-card" autocomplete="off" action="{{ route('store_settings') }}">
                            @csrf
                            <div class="row">
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Twitter') }}</label>
                                        <input type="text" class="form-control" name="twitter" value="{{ get_option('twitter') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Telegram') }}</label>
                                        <input type="text" class="form-control" name="telegram" value="{{ get_option('telegram') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Youtube') }}</label>
                                        <input type="text" class="form-control" name="youtube" value="{{ get_option('youtube') }}" required>
                                    </div>
                                </div>
                                
                                <div class="col-md-12">
                                    <div class="form-group text-right">
                                        <button type="submit" class="btn btn-primary btn-sm">
                                            {{ _lang('Update') }}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </form>
                        <h3 class="mb-3 mt-3 header-title card-title">{{ _lang('Privacy Policy') }}</h3>
                        <form method="post" class="ajax-submit2 params-card" autocomplete="off" action="{{ route('store_settings') }}">
                            @csrf
                            <div class="row">
                                <div class="col-md-12">
                                    <div class="form-group">
                                        <textarea name="privacy_policy" class="form-control summernote" rows="4" required>{{ get_option('privacy_policy') }}</textarea>
                                    </div>
                                </div>
                                
                                <div class="col-md-12">
                                    <div class="form-group text-right">
                                        <button type="submit" class="btn btn-primary btn-sm">
                                            {{ _lang('Update') }}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </form>
                        <h3 class="mb-3 mt-3 header-title card-title">{{ _lang('Terms & Conditions') }}</h3>
                        <form method="post" class="ajax-submit2 params-card" autocomplete="off" action="{{ route('store_settings') }}">
                            @csrf
                            <div class="row">
                                <div class="col-md-12">
                                    <div class="form-group">
                                        <textarea name="terms_conditions" class="form-control summernote" rows="4" required>{{ get_option('terms_conditions') }}</textarea>
                                    </div>
                                </div>
                                
                                <div class="col-md-12">
                                    <div class="form-group text-right">
                                        <button type="submit" class="btn btn-primary btn-sm">
                                            {{ _lang('Update') }}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
            <div class="tab-pane fade" id="v-pills-android" role="tabpanel" aria-labelledby="v-pills-android-tab">
                <div class="card">
                    <div class="card-body">
                        <h3 class="mb-3 mt-3 header-title card-title">{{ _lang('Live Settings') }}</h3>
                        <form method="post" class="ajax-submit2 params-card" autocomplete="off" action="{{ route('store_settings') }}">
                            @csrf
                            <div class="row">
                               <div class="col-md-12">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Enable Live') }}</label>
                                        <select class="form-control select2" name="android_enable_live" data-selected="{{ get_option('android_enable_live', '1') }}" required>
                                            <option value="0">{{ _lang('No') }}</option>
                                            <option value="1">{{ _lang('Yes') }}</option>
                                        </select>
                                    </div>
                                </div>
                                

                                <div class="col-md-12">
                                    <div class="form-group text-right">
                                        <button type="submit" class="btn btn-primary btn-sm">
                                            {{ _lang('Update') }}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </form>
                        <h3 class="mb-3 mt-3 header-title card-title">{{ _lang('Ads Settings') }}</h3>
                        <form method="post" class="ajax-submit2 params-card" autocomplete="off" action="{{ route('store_settings') }}">
                            @csrf
                            <div class="row">
                               <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Enable Ads') }}</label>
                                        <select class="form-control select2" name="android_enable_ads" data-selected="{{ get_option('android_enable_ads', '0') }}" required>
                                            <option value="0">{{ _lang('No') }}</option>
                                            <option value="1">{{ _lang('Yes') }}</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Ads Type') }}</label>
                                        <select class="form-control select2" name="android_ads_type" data-selected="{{ get_option('android_ads_type', 'google') }}" required>
                                            <option value="google">{{ _lang('Google') }}</option>
                                            <option value="facebook">{{ _lang('Facebook Audience Network') }}</option>
                                            <option value="applovin">{{ _lang('Applovin') }}</option>
                                        </select>
                                    </div>
                                </div>
                                
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Application Id') }}</label>
                                        <input type="text" class="form-control" name="android_application_id" value="{{ get_option('android_application_id', '#') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Appopen Ad Code') }} (Inline Ad code or Applovin)</label>
                                        <input type="text" class="form-control" name="android_appopen_ad_code" value="{{ get_option('android_appopen_ad_code', '#') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Banner Ad Code') }}</label>
                                        <input type="text" class="form-control" name="android_banner_ad_code" value="{{ get_option('android_banner_ad_code', '#') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Native Ad Code') }}</label>
                                        <input type="text" class="form-control" name="android_native_ad_code" value="{{ get_option('android_native_ad_code', '#') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Interstitial Ad Code') }}</label>
                                        <input type="text" class="form-control" name="android_interstitial_ad_code" value="{{ get_option('android_interstitial_ad_code', '#') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Interstitial Ad Click') }}</label>
                                        <select class="form-control select2" name="android_interstitial_ad_click" data-selected="{{ get_option('android_interstitial_ad_click', '3') }}" required>
                                            @for ($i = 1; $i <= 10; $i++)
                                                <option value="{{ $i }}" >{{ $i }}</option>
                                            @endfor
                                        </select>
                                    </div>
                                </div>

                                <div class="col-md-12">
                                    <div class="form-group text-right">
                                        <button type="submit" class="btn btn-primary btn-sm">
                                            {{ _lang('Update') }}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </form>
                        <h3 class="mb-3 mt-3 header-title card-title">{{ _lang('Notification') }}</h3>
                        <form method="post" class="ajax-submit2 params-card" autocomplete="off" action="{{ route('store_settings') }}">
                            @csrf
                            <div class="row">
                                <div class="col-md-12">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Notification Type') }}</label>
                                        <select class="form-control select2" name="android_notification_type" data-selected="{{ get_option('android_notification_type', 'fcm') }}" required>
                                            {{-- <option value="onesignal">{{ _lang('One Signal') }}</option> --}}
                                            <option value="fcm">{{ _lang('FCM') }}</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="col-md-6 android_onesignal d-none">
                                    <div class="form-group">
                                        <label class="form-control-label">One Signal App ID</label>
                                        <input type="text" name="android_onesignal_app_id" class="form-control" value="{{ get_option('android_onesignal_app_id', 'N/A') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6 android_onesignal d-none">
                                    <div class="form-group">
                                        <label class="form-control-label">One Signal Api Key</label>
                                        <input type="text" name="android_onesignal_api_key" class="form-control" value="{{ get_option('android_onesignal_api_key', 'N/A') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6 android_fcm d-none">
                                    <div class="form-group">
                                        <label class="form-control-label">Firebase Server Key</label>
                                        <input type="text" name="android_firebase_server_key" class="form-control" value="{{ get_option('android_firebase_server_key', 'N/A') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6 android_fcm d-none">
                                    <div class="form-group">
                                        <label class="form-control-label">Firebase Topics</label>
                                        <input type="text" name="android_firebase_topics" class="form-control" value="{{ get_option('android_firebase_topics', 'N/A') }}" disabled required>
                                    </div>
                                </div>
                                <div class="col-md-12">
                                    <div class="form-group text-right">
                                        <button type="submit" class="btn btn-primary btn-sm">
                                            {{ _lang('Update') }}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
            <div class="tab-pane fade" id="v-pills-ios" role="tabpanel" aria-labelledby="v-pills-ios-tab">
                <div class="card">
                    <div class="card-body">
                        <h3 class="mb-3 mt-3 header-title card-title">{{ _lang('Live Settings') }}</h3>
                        <form method="post" class="ajax-submit2 params-card" autocomplete="off" action="{{ route('store_settings') }}">
                            @csrf
                            <div class="row">
                               <div class="col-md-12">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Enable Live') }}</label>
                                        <select class="form-control select2" name="ios_enable_live" data-selected="{{ get_option('ios_enable_live', '1') }}" required>
                                            <option value="0">{{ _lang('No') }}</option>
                                            <option value="1">{{ _lang('Yes') }}</option>
                                        </select>
                                    </div>
                                </div>
                                

                                <div class="col-md-12">
                                    <div class="form-group text-right">
                                        <button type="submit" class="btn btn-primary btn-sm">
                                            {{ _lang('Update') }}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </form>
                        <h3 class="mb-3 mt-3 header-title card-title">{{ _lang('Ads Settings') }}</h3>
                        <form method="post" class="ajax-submit2 params-card" autocomplete="off" action="{{ route('store_settings') }}">
                            @csrf
                            <div class="row">
                               <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Enable Ads') }}</label>
                                        <select class="form-control select2" name="ios_enable_ads" data-selected="{{ get_option('ios_enable_ads', '0') }}" required>
                                            <option value="0">{{ _lang('No') }}</option>
                                            <option value="1">{{ _lang('Yes') }}</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Ads Type') }}</label>
                                        <select class="form-control select2" name="ios_ads_type" data-selected="{{ get_option('ios_ads_type', 'google') }}" required>
                                            <option value="google">{{ _lang('Google') }}</option>
                                            <option value="facebook">{{ _lang('Facebook Audience Network') }}</option>
                                            <option value="applovin">{{ _lang('Applovin') }}</option>
                                        </select>
                                    </div>
                                </div>
                                
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Application Id') }}</label>
                                        <input type="text" class="form-control" name="ios_application_id" value="{{ get_option('ios_application_id', '#') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Appopen Ad Code') }} (Inline Ad code or Applovin)</label>
                                        <input type="text" class="form-control" name="ios_appopen_ad_code" value="{{ get_option('ios_appopen_ad_code', '#') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Banner Ad Code') }}</label>
                                        <input type="text" class="form-control" name="ios_banner_ad_code" value="{{ get_option('ios_banner_ad_code', '#') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Native Ad Code') }}</label>
                                        <input type="text" class="form-control" name="ios_native_ad_code" value="{{ get_option('ios_native_ad_code', '#') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Interstitial Ad Code') }}</label>
                                        <input type="text" class="form-control" name="ios_interstitial_ad_code" value="{{ get_option('ios_interstitial_ad_code', '#') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Interstitial Ad Click') }}</label>
                                        <select class="form-control select2" name="ios_interstitial_ad_click" data-selected="{{ get_option('ios_interstitial_ad_click', '3') }}" required>
                                            @for ($i = 1; $i <= 10; $i++)
                                                <option value="{{ $i }}" >{{ $i }}</option>
                                            @endfor
                                        </select>
                                    </div>
                                </div>

                                <div class="col-md-12">
                                    <div class="form-group text-right">
                                        <button type="submit" class="btn btn-primary btn-sm">
                                            {{ _lang('Update') }}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </form>
                        <h3 class="mb-3 mt-3 header-title card-title">{{ _lang('Notification') }}</h3>
                        <form method="post" class="ajax-submit2 params-card" autocomplete="off" action="{{ route('store_settings') }}">
                            @csrf
                            <div class="row">
                                <div class="col-md-12">
                                    <div class="form-group">
                                        <label class="control-label">{{ _lang('Notification Type') }}</label>
                                        <select class="form-control select2" name="ios_notification_type" data-selected="{{ get_option('ios_notification_type', 'fcm') }}" required>
                                            {{-- <option value="onesignal">{{ _lang('One Signal') }}</option> --}}
                                            <option value="fcm">{{ _lang('FCM') }}</option>
                                        </select>
                                    </div>
                                </div>
                                <div class="col-md-6 ios_onesignal d-none">
                                    <div class="form-group">
                                        <label class="form-control-label">One Signal App ID</label>
                                        <input type="text" name="ios_onesignal_app_id" class="form-control" value="{{ get_option('ios_onesignal_app_id', 'N/A') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6 ios_onesignal d-none">
                                    <div class="form-group">
                                        <label class="form-control-label">One Signal Api Key</label>
                                        <input type="text" name="ios_onesignal_api_key" class="form-control" value="{{ get_option('ios_onesignal_api_key', 'N/A') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6 ios_fcm d-none">
                                    <div class="form-group">
                                        <label class="form-control-label">Firebase Server Key</label>
                                        <input type="text" name="ios_firebase_server_key" class="form-control" value="{{ get_option('ios_firebase_server_key', 'N/A') }}" required>
                                    </div>
                                </div>
                                <div class="col-md-6 ios_fcm d-none">
                                    <div class="form-group">
                                        <label class="form-control-label">Firebase Topics</label>
                                        <input type="text" name="ios_firebase_topics" class="form-control" value="{{ get_option('ios_firebase_topics', 'N/A') }}" disabled required>
                                    </div>
                                </div>
                                <div class="col-md-12">
                                    <div class="form-group text-right">
                                        <button type="submit" class="btn btn-primary btn-sm">
                                            {{ _lang('Update') }}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
            
        </div>
    </div>
</div>
@endsection

@section('js-script')
<script type="text/javascript">
    @if(get_option('android_notification_type', 'fcm') == 'onesignal')
    $('.android_onesignal').removeClass('d-none').find('input').attr('disabled', false);
    $('.android_fcm').addClass('d-none').find('input').attr('disabled', true);
    @else
    $('.android_fcm').removeClass('d-none').find('input').attr('disabled', false);
    $('.android_onesignal').addClass('d-none').find('input').attr('disabled', true);
    @endif        
    $('[name=android_notification_type]').on('change', function() {
        if($(this).val() == 'onesignal'){
            $('.android_onesignal').removeClass('d-none').find('input').attr('disabled', false);
            $('.android_fcm').addClass('d-none').find('input').attr('disabled', true);
        }else{
            $('.android_fcm').removeClass('d-none').find('input').attr('disabled', false);
            $('.android_onesignal').addClass('d-none').find('input').attr('disabled', true);
        }
    });

    @if(get_option('ios_notification_type', 'fcm') == 'onesignal')
    $('.ios_onesignal').removeClass('d-none').find('input').attr('disabled', false);
    $('.ios_fcm').addClass('d-none').find('input').attr('disabled', true);
    @else
    $('.ios_fcm').removeClass('d-none').find('input').attr('disabled', false);
    $('.ios_onesignal').addClass('d-none').find('input').attr('disabled', true);
    @endif        
    $('[name=ios_notification_type]').on('change', function() {
        if($(this).val() == 'onesignal'){
            $('.ios_onesignal').removeClass('d-none').find('input').attr('disabled', false);
            $('.ios_fcm').addClass('d-none').find('input').attr('disabled', true);
        }else{
            $('.ios_fcm').removeClass('d-none').find('input').attr('disabled', false);
            $('.ios_onesignal').addClass('d-none').find('input').attr('disabled', true);
        }
    });
</script>
@endsection

