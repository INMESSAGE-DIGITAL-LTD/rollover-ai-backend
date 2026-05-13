<?php

namespace App\Http\Controllers\Api\v1;

use App\Http\Controllers\Controller;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Mail;
use App\Mail\InvoiceMail;
use App\Models\Subscription;
use App\Models\Payment;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Validator;

class SubscriptionController extends Controller
{
    // Subscription List
    public function subscriptions(Request $request)
    {
        $validator = Validator::make($request->all(), [

            'platform' => 'required|string|max:20',
            
        ]);

        if ($validator->fails()) {
            return response()->json(['result' => false, 'message' => $validator->errors()->first()]);
        }

        $platform = $request->platform;

        $subscriptions = Cache::rememberForever("subscriptions_$platform", function () use ($platform){

            $where = [];
            $where['status'] = 1;
            $where['platform'] = $platform;
            $subscriptions = Subscription::where($where)
                                            ->orderBy('position', 'ASC')
                                            ->get();

            return $subscriptions;
        });
        
        $status = true;

        return response()->json(['status' => $status, 'data' => $subscriptions]);
    }

    // Update Subscription
    public function subscription_update(Request $request)
    {
        $validator = Validator::make($request->all(), [

            'subscription_id' => 'required|string',
            'amount' => 'required|string',
            'platform' => 'required|string|max:20',
            'sid' => 'required_if:platform,web|string'
            
        ]);

        if ($validator->fails()) {
            return response()->json(['result' => false, 'message' => $validator->errors()->first()]);
        }

        $user = $request->user();
        $payment = new Payment();

        // Check User Subscription & Payment Activate or Not for Web
        if($request->platform == 'web')
        {
            $payment_exists = Payment::where('sid', $request->sid)->first();
            
            if($payment_exists)
            {
                $user->subscription_name = $user->subscription->name;
                return response()->json([
                    'status' => true,
                    'data' => $user->makeHidden(['id', 'user_type', 'created_at', 'updated_at', 'apps', 'app_id', 'email_verified_at', 'status', 'subscription', 'verification', 'forget_code']),
                ]);
            }
            else
            {
                $subscription = Subscription::find($request->subscription_id);

                if($user->expired_at != null && $user->expired_at > now())
                {
                    $expired_at = $user->expired_at;
                    $date = date("Y-m-d H:i:s", strtotime("+{$subscription->duration} {$subscription->duration_type}", \Carbon\Carbon::parse($expired_at)->timestamp));
                }
                else
                {
                    $date = date("Y-m-d H:i:s", strtotime("+{$subscription->duration} {$subscription->duration_type}", now()->timestamp));
                }

                $user->expired_at = $date;
                $user->subscription_id = $subscription->id;
                $user->subscribe_from_web = 1;

                $user->save();

                $payment->user_id = $user->id;
                $payment->subscription_id = $subscription->id;
                $payment->date = now();
                $payment->amount = $request->amount;
                $payment->platform = $request->platform;

                $payment->save();

                Cache::forget("payments_" . $user->id);

                $user->subscription_name = $user->subscription->name;

                // Send Mail
                $this->send_message($user, $payment, "Subscription Invoice", "Subscription Invoice");

                return response()->json([
                    'status' => true,
                    'data' => $user->makeHidden(['id', 'user_type', 'created_at', 'updated_at', 'apps', 'app_id', 'email_verified_at', 'status', 'subscription', 'verification', 'forget_code']),
                ]);
            }
        }
        else
        {
            $subscription = Subscription::find($request->subscription_id);
    
            if($user->expired_at != null && $user->expired_at > now())
            {
                $expired_at = $user->expired_at;
                $date = date("Y-m-d H:i:s", strtotime("+{$subscription->duration} {$subscription->duration_type}", \Carbon\Carbon::parse($expired_at)->timestamp));
            }
            else
            {
                $date = date("Y-m-d H:i:s", strtotime("+{$subscription->duration} {$subscription->duration_type}", now()->timestamp));
            }
    
            $user->expired_at = $date;
            $user->subscription_id = $subscription->id;
    
            $user->save();
    
            $payment->user_id = $user->id;
            $payment->subscription_id = $subscription->id;
            $payment->date = now();
            $payment->amount = $request->amount;
            $payment->platform = $request->platform;
    
            $payment->save();

            Cache::forget("payments_" . $user->id);

            $user->subscription_name = $user->subscription->name;

            // Send Mail
            $this->send_message($user, $payment, "Subscription Invoice", "Subscription Invoice");
            
            return response()->json([
                'status' => true,
                'data' => $user->makeHidden(['id', 'user_type', 'created_at', 'updated_at', 'apps', 'app_id', 'email_verified_at', 'status', 'subscription', 'verification', 'forget_code']),
            ]);
        }
    }

    // Subscription Expired
    public function subscription_expired(Request $request)
    {
        $user = $request->user();

        $user->subscription_id = 0;
        $user->expired_at = null;

        $user->save();

        $user->email = $user->email;
        $user->subscription_name = $user->subscription->name;
        
        return response()->json([
            'status' => true,
            'data' => $user->makeHidden(['id', 'user_type', 'created_at', 'updated_at', 'apps', 'app_id', 'email_verified_at', 'status', 'subscription']),
        ]);
    }

    // Subscription Restore
    public function subscription_restore(Request $request)
    {
        $validator = Validator::make($request->all(), [

            'product_id' => 'required|string',
            
        ]);

        if ($validator->fails()) {
            return response()->json(['result' => false, 'message' => $validator->errors()->first()]);
        }

        $user = $request->user();

        $subscription = Subscription::where('product_id', $request->product_id)->first();
        
        if(!$subscription){
            return response()->json(['result' => false, 'message' => 'Product not found.']);
        }

        $payments = Payment::where('user_id', $user->id)
                        ->where('subscription_id', $subscription->id)
                        ->first();

        if(!$payments){
            return response()->json(['result' => false, 'message' => 'illegal activity.']);
        }
                      
        if($user->expired_at != null && $user->expired_at > now()){
            $expired_at = $user->expired_at;
            $date = date("Y-m-d H:i:s", strtotime("+{$subscription->duration} {$subscription->duration_type}", \Carbon\Carbon::parse($expired_at)->timestamp));
        }else{
            $date = date("Y-m-d H:i:s", strtotime("+{$subscription->duration} {$subscription->duration_type}", now()->timestamp));
        }

        $user->expired_at = $date;
        $user->subscription_id = $subscription->id;

        $user->save();

        $user->subscription_name = $user->subscription->name;
        
        return response()->json([
            'status' => true,
            'user' => $user->makeHidden(['id', 'user_type', 'created_at', 'updated_at', 'apps', 'app_id', 'email_verified_at', 'status', 'subscription']),
        ]);
    }

    // Payment
    public function payments(Request $request)
    {
        $user = $request->user();
        $payments = Cache::rememberForever("payments_{$user->id}", function () use ($user){
            $payments = Payment::select('date', 'amount', 'subscriptions.name AS subscription_name', 'duration', 'duration_type')
                            ->join('subscriptions', 'subscriptions.id', 'subscription_id')
                            ->where('user_id', $user->id)
                            ->orderBy('payments.id', 'DESC')
                            ->get();
            return $payments;
        });
        
        $status = true;

        return response()->json(['status' => $status, 'data' => $payments]);
    }

    // Send Mail
    public function send_message($user, $payment, $subject, $message)
    {
        @ini_set('max_execution_time', 0);
        @set_time_limit(0);

        // Timezone
        config(['app.timezone' => get_option('timezone')]);

        // Email
        config(['mail.driver' => 'smtp']);
        config(['mail.from.name' => get_option('from_name')]);
        config(['mail.from.address' => get_option('from_mail')]);
        config(['mail.host' => get_option('smtp_host')]);
        config(['mail.port' => get_option('smtp_port')]);
        config(['mail.username' => get_option('smtp_username')]);
        config(['mail.password' => get_option('smtp_password')]);
        config(['mail.encryption' => get_option('smtp_encryption')]);

        
        $mail  = new \stdClass();
        $mail->name = $user->name;
        $mail->email = $user->email;
        $mail->subject = $subject;
        $mail->message = $message;
        $mail->payment = $payment;
        $mail->user = $user;
        $mail->app_name = get_option('from_name');


        try {
            Mail::to($user->email)->send(new InvoiceMail($mail));
            return json_encode(array('result' => true, 'message' => _lang('Your Message send sucessfully.')));
        } catch (\Exception $e) {
            return json_encode(array('result' => false, 'message' => _lang('Error Occured, Please try again !')));
        }
    }
}
