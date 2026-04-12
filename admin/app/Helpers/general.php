<?php

if ( ! function_exists('_lang')){
    function _lang($string = ''){

        return $string;
    }
}

if ( ! function_exists('get_lang')){
    function get_lang($string = ''){
        $set_lang = Session::get('_lang');
        $default_lang = get_option('language');
        $lang = (($set_lang != '') ? $set_lang : $default_lang);
        return $lang;
    }
}

if ( ! function_exists('get_leagues')){
    function get_leagues(){

        $json = json_decode(file_get_contents(app_path() . '/Helpers/leagues.json')); 

        return $json->response;
    }
}

if ( ! function_exists('user')){
    function user(){
        return \Auth::user();
    }
}

if (!function_exists('send_notification')) {
    function send_notification($notification, $data = [])
    {
        
        send_notification_core('android', $notification, $data);
        //send_notification_core('ios', $notification, $data);

        return true;
    }
}

if (!function_exists('send_notification_core')) {
    function send_notification_core($platform, $notification, $additional_data = [])
    {
        $notification_type = "{$platform}_prediction_app_notification_type";
        $onesignal_app_id = "{$platform}_prediction_app_onesignal_app_id";
        $onesignal_api_key = "{$platform}_prediction_app_onesignal_api_key";
        $firebase_server_key = "{$platform}_prediction_app_firebase_server_key";
        $firebase_topics = "{$platform}_prediction_app_firebase_topics";

        $title = $notification->title;
        $body = $notification->message;
        $image = $notification->image;

        if(get_option($notification_type) == 'onesignal'){
            //
        }else{
            
            $credentialsFilePath = app_path() . '/Helpers/fcm.json';
            $client = new \Google_Client();
            $client->setAuthConfig($credentialsFilePath);
            $client->addScope('https://www.googleapis.com/auth/firebase.messaging');
            $apiurl = 'https://fcm.googleapis.com/v1/projects/wise-bet/messages:send';
            $client->refreshTokenWithAssertion();
            $token = $client->getAccessToken();
            $access_token = $token['access_token'];
            
            $headers = [
                 "Authorization: Bearer $access_token",
                 'Content-Type: application/json'
            ];
  
            $payload = [
                "message" => [
                    "topic" => 'high_importance_channel', 
                    "notification" => [
                        "title" => $title, 
                        "body"=> $body,
                    ],
                    "apns" => [
                        "payload" => [
                            "aps" => [
                                "mutable-content" => 1
                            ]
                        ],
                        "fcm_options" => [
                            "image" => $image
                        ]
                    ],
                    "android" => [
                        "priority" => "HIGH",
                        "notification" => [
                            "default_sound" => true,
                            "image" => $image
                        ]
                    ]
                ]
            ];
            
            $payload = json_encode($payload);
            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, $apiurl);
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
            curl_exec($ch);
            
            $res = curl_close($ch);
            
        }

        return true;
    }
}

if (!function_exists('prediction_app_send_notification')) {
    function prediction_app_send_notification($notification, $data = [])
    {
        
        prediction_app_send_notification_core('android', $notification, $data);
        //prediction_app_send_notification_core('ios', $notification, $data);

        return true;
    }
}

if (!function_exists('prediction_app_send_notification_core')) {
    function prediction_app_send_notification_core($platform, $notification, $additional_data = [])
    {
        $notification_type = "{$platform}_prediction_app_notification_type";
        $onesignal_app_id = "{$platform}_prediction_app_onesignal_app_id";
        $onesignal_api_key = "{$platform}_prediction_app_onesignal_api_key";
        $firebase_server_key = "{$platform}_prediction_app_firebase_server_key";
        $firebase_topics = "{$platform}_prediction_app_firebase_topics";

        $title = $notification->title;
        $body = $notification->message;
        $image = $notification->image;

        if(get_option($notification_type) == 'onesignal'){
            //
        }else{
            
            $credentialsFilePath = app_path() . '/Helpers/fcm.json';
            $client = new \Google_Client();
            $client->setAuthConfig($credentialsFilePath);
            $client->addScope('https://www.googleapis.com/auth/firebase.messaging');
            $apiurl = 'https://fcm.googleapis.com/v1/projects/wise-bet/messages:send';
            $client->refreshTokenWithAssertion();
            $token = $client->getAccessToken();
            $access_token = $token['access_token'];
            
            $headers = [
                 "Authorization: Bearer $access_token",
                 'Content-Type: application/json'
            ];
  
            $payload = [
                "message" => [
                    "topic" => 'high_importance_channel', 
                    "notification" => [
                        "title" => $title, 
                        "body"=> $body,
                    ],
                    "apns" => [
                        "payload" => [
                            "aps" => [
                                "mutable-content" => 1
                            ]
                        ],
                        "fcm_options" => [
                            "image" => $image
                        ]
                    ],
                    "android" => [
                        "priority" => "HIGH",
                        "notification" => [
                            "default_sound" => true,
                            "image" => $image
                        ]
                    ]
                ]
            ];
            
            $payload = json_encode($payload);
            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, $apiurl);
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
            curl_exec($ch);
            
            $res = curl_close($ch);
        }

        return true;
    }
}

if (!function_exists('real_app_send_notification')) {
    function real_app_send_notification($notification, $data = [])
    {
        
        real_app_send_notification_core('ios', $notification, $data);
        //prediction_app_send_notification_core('ios', $notification, $data);

        return true;
    }
}

if (!function_exists('real_app_send_notification_core')) {
    function real_app_send_notification_core($platform, $notification, $additional_data = [])
    {
        $notification_type = "firebase";
        $firebase_topics = "high_importance_channel";
        $projectId = "real-betting-tips-293b1";

        $title = $notification->title;
        $body = $notification->message;
        $image = $notification->image;

        if(get_option($notification_type) == 'onesignal'){
            //
        }else{
            
            $credentialsFilePath = app_path() . '/Helpers/real_app.json';
            $client = new \Google_Client();
            $client->setAuthConfig($credentialsFilePath);
            $client->addScope('https://www.googleapis.com/auth/firebase.messaging');
            $apiurl = "https://fcm.googleapis.com/v1/projects/$projectId/messages:send";
            $client->refreshTokenWithAssertion();
            $token = $client->getAccessToken();
            $access_token = $token['access_token'];
            
            $headers = [
                 "Authorization: Bearer $access_token",
                 'Content-Type: application/json'
            ];
  
            $payload = [
                "message" => [
                    "topic" => $firebase_topics, 
                    "notification" => [
                        "title" => $title, 
                        "body"=> $body,
                    ],
                    "apns" => [
                        "payload" => [
                            "aps" => [
                                "mutable-content" => 1
                            ]
                        ],
                        "fcm_options" => [
                            "image" => $image
                        ]
                    ],
                    "android" => [
                        "priority" => "HIGH",
                        "notification" => [
                            "default_sound" => true,
                            "image" => $image
                        ]
                    ]
                ]
            ];
            
            $payload = json_encode($payload);
            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, $apiurl);
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
            curl_exec($ch);
            
            $res = curl_close($ch);
            
        }

        return true;
    }
}

if (!function_exists('buildTree')) {

    function buildTree($object, $currentParent, $url, $currLevel = 0, $prevLevel = -1)
    {
        foreach ($object as $category) {
            if ($currentParent == $category->parent_id) {
                if ($currLevel > $prevLevel) {
                    echo "<ul class='menutree'>";
                }
                if ($currLevel == $prevLevel) {
                    echo "</li>";
                }
                echo '<li> <label class="menu_label" for=' . $category->id . '><a href="' . route($url, $category->id) . '" class="ajax-modal" title="' . _lang('Details') . '">' . $category->name . '</a><a href="' . route($url, $category->id) . '" class="btn btn-warning btn-xs float-right">' . _lang('Edit') . '</a></label>';
                if ($currLevel > $prevLevel) {
                    $prevLevel = $currLevel;
                }
                $currLevel++;
                buildTree($object, $category->id, $url, $currLevel, $prevLevel);
                $currLevel--;
            }
        }
        if ($currLevel == $prevLevel) {
            echo "</li> </ul>";
        }
    }
}

if (!function_exists('settings')) {
    function settings($name, $value = '')
    {
        $setting = \App\Setting::where('name', $name)->first();
        if (! $setting) {
            $setting = new \App\Setting();
            $setting->name = $name;
            $setting->value = $value;
            $setting->save();
            return $setting;
        }

        $setting->value = $value;
        $setting->save();
        return $setting;
    }
}

if (!function_exists('create_option')) {
    function create_option($table = '', $value = '', $show = '', $selected = '', $where = null)
    {
        $options = '';
        $condition = '';
        
        if($where != NULL){
            $condition .= "WHERE ";
            foreach( $where as $key => $v ){
                $condition.= $key . "'" . $v . "'";
            }
        }

        if (is_array($show)){
            $concatenation = $show[0];
            array_shift($show);
            $p = implode(",", $show);
            $results = DB::select("SELECT $value, (CONCAT_WS('$concatenation', $p)) AS d FROM $table $condition");
        }else{
            $results = DB::select("SELECT * FROM $table $condition");
        }

        foreach($results as $data){
            if($selected == $data->$value){   
                if(! is_array($show)){
                    $options .= "<option value='" . $data->$value . "' selected>" . ucwords($data->$show) . "</option>";
                }else{
                    $options .= "<option value='" . $data->$value . "' selected>" . ucwords($data->d) . "</option>";
                }
            }else{
                if(! is_array($show)){
                    $options .= "<option value='" . $data->$value . "'>" . ucwords($data->$show) . "</option>";
                }else{
                    $options .= "<option value='" . $data->$value . "'>" . ucwords($data->d) . "</option>";
                }
            } 
        }
        
        echo $options;
    }
}

if (!function_exists('time_elapsed_string')) {
    function time_elapsed_string($datetime, $full = false)
    {
        $now = new \DateTime;
        $ago = new \DateTime($datetime);
        $diff = $now->diff($ago);

        $diff->w = floor($diff->d / 7);
        $diff->d -= $diff->w * 7;

        $string = array(
            'y' => 'year',
            'm' => 'month',
            'w' => 'week',
            'd' => 'day',
            'h' => 'hour',
            'i' => 'minute',
            's' => 'second',
        );
        foreach ($string as $k => &$v) {
            if ($diff->$k) {
                $v = $diff->$k . ' ' . $v . ($diff->$k > 1 ? 's' : '');
            } else {
                unset($string[$k]);
            }
        }

        if (!$full) {
            $string = array_slice($string, 0, 1);
        }

        return $string ? implode(', ', $string) . ' ago' : 'just now';
    }
}

if (!function_exists('get_table')) {
    function get_table($table, $where = null, $order = 'DESC')
    {
        if ($where != null) {
            $results = DB::table($table)->where($where)->orderBy('id', $order)->get();
        } else {
            $results = DB::table($table)->orderBy('id', $order)->get();
        }
        return $results;
    }
}

if (!function_exists('get_logo')) {
    function get_logo()
    {
        $logo = get_option("logo");
        if ($logo == '') {
            return asset("public/default/default-logo.png");
        }
        return asset("public/uploads/images/$logo");
    }
}

if (!function_exists('get_icon')) {
    function get_icon()
    {
        $icon = get_option("icon");

        if ($icon == '') {
            return asset("public/default/default-icon.png");
        }
        return asset("public/uploads/images/$icon");
    }
}

if (!function_exists('get_option')) {
    function get_option($name, $optional = '')
    {
        $setting = DB::table('settings')->where('name', $name)->get();
        if (!$setting->isEmpty()) {
            return $setting[0]->value;
        }
        return $optional;

    }
}

if (!function_exists('file_settings')) {
    function file_settings($max_upload_size = null, $file_type_supported = null)
    {
        if (!$max_upload_size) {
            $max_upload_size = (get_option('max_upload_size', 5) * 1024);
        }
        if (!$file_type_supported) {
            $file_type_supported = get_option('file_type_supported', 'PNG,JPG,JPEG,png,jpg,jpeg');
        }
        return "|max:$max_upload_size|mimes:$file_type_supported";
    }
}

if (!function_exists('status')) {
    function status($label, $badge, $raw = true)
    {
        return '<span class="badge badge-' . $badge . '">' . $label . '</span>';
    }
}

if (!function_exists('counter')) {
    function counter($table, $where = null)
    {
        if ($where) {
            $count = DB::table($table)->where($where)->count('id');
        } else {
            $count = DB::table($table)->count('id');
        }
        return $count;
    }
}

if (!function_exists('timezone_list')) {
    function timezone_list()
    {
        $zones_array = array();
        $timestamp = time();
        foreach (timezone_identifiers_list() as $key => $zone) {
            date_default_timezone_set($zone);
            $zones_array[$key]['ZONE'] = $zone;
            $zones_array[$key]['GMT'] = 'UTC/GMT ' . date('P', $timestamp);
        }
        return $zones_array;
    }

}

if (!function_exists('create_timezone_option')) {

    function create_timezone_option($old = "")
    {
        $option = "";
        $timestamp = time();
        foreach (timezone_identifiers_list() as $key => $zone) {
            date_default_timezone_set($zone);
            $selected = $old == $zone ? "selected" : "";
            $option .= '<option value="' . $zone . '"' . $selected . '>' . 'GMT ' . date('P', $timestamp) . ' ' . $zone . '</option>';
        }
        echo $option;
    }

}

if (!function_exists('get_country_list')) {
    function get_country_list($selected = '')
    {
        if ($selected == "") {
            echo file_get_contents(app_path() . '/Helpers/country.txt');
        } else {
            $pattern = '<option value="' . $selected . '">';
            $replace = '<option value="' . $selected . '" selected="selected">';
            $country_list = file_get_contents(app_path() . '/Helpers/country.txt');
            $country_list = str_replace($pattern, $replace, $country_list);
            echo $country_list;
        }
    }
}

if (!function_exists('load_language')) {
    function load_language($active = '')
    {
        $path = resource_path() . "/_lang";
        $files = scandir($path);
        $options = "";
        foreach ($files as $file) {
            $name = pathinfo($file, PATHINFO_FILENAME);
            if ($name == "." || $name == "" || $name == "language") {
                continue;
            }
            $selected = "";
            if ($active == $name) {
                $selected = "selected";
            } else {
                $selected = "";
            }
            $options .= "<option value='$name' $selected>" . ucwords($name) . "</option>";
        }
        echo $options;
    }
}

if (!function_exists('get_language_list')) {
    function get_language_list()
    {
        $path = resource_path() . "/_lang";
        $files = scandir($path);
        $array = array();

        $default = get_option('language');
        $array[] = $default;

        foreach ($files as $file) {
            $name = pathinfo($file, PATHINFO_FILENAME);
            if ($name == "." || $name == "" || $name == "language" || $name == $default) {
                continue;
            }

            $array[] = $name;

        }
        return $array;
    }
}

if (!function_exists('sql_escape')) {
    function sql_escape($unsafe_str) {
        if (get_magic_quotes_gpc()) {
            $unsafe_str = stripslashes($unsafe_str);
        }
        return $escaped_str = str_replace("'", "", $unsafe_str);
    }
}

if (!function_exists('xss_clean')) {
    function xss_clean($data) {
        // Fix &entity\n;
        $data = str_replace(array('&amp;', '&lt;', '&gt;'), array('&amp;amp;', '&amp;lt;', '&amp;gt;'), $data);
        $data = preg_replace('/(&#*\w+)[\x00-\x20]+;/u', '$1;', $data);
        $data = preg_replace('/(&#x*[0-9A-F]+);*/iu', '$1;', $data);
        $data = html_entity_decode($data, ENT_COMPAT, 'UTF-8');

        // Remove any attribute starting with "on" or xmlns
        $data = preg_replace('#(<[^>]+?[\x00-\x20"\'])(?:on|xmlns)[^>]*+>#iu', '$1>', $data);

        // Remove javascript: and vbscript: protocols
        $data = preg_replace('#([a-z]*)[\x00-\x20]*=[\x00-\x20]*([`\'"]*)[\x00-\x20]*j[\x00-\x20]*a[\x00-\x20]*v[\x00-\x20]*a[\x00-\x20]*s[\x00-\x20]*c[\x00-\x20]*r[\x00-\x20]*i[\x00-\x20]*p[\x00-\x20]*t[\x00-\x20]*:#iu', '$1=$2nojavascript...', $data);
        $data = preg_replace('#([a-z]*)[\x00-\x20]*=([\'"]*)[\x00-\x20]*v[\x00-\x20]*b[\x00-\x20]*s[\x00-\x20]*c[\x00-\x20]*r[\x00-\x20]*i[\x00-\x20]*p[\x00-\x20]*t[\x00-\x20]*:#iu', '$1=$2novbscript...', $data);
        $data = preg_replace('#([a-z]*)[\x00-\x20]*=([\'"]*)[\x00-\x20]*-moz-binding[\x00-\x20]*:#u', '$1=$2nomozbinding...', $data);

        // Only works in IE: <span style="width: expression(alert('Ping!'));"></span>
        $data = preg_replace('#(<[^>]+?)style[\x00-\x20]*=[\x00-\x20]*[`\'"]*.*?expression[\x00-\x20]*\([^>]*+>#i', '$1>', $data);
        $data = preg_replace('#(<[^>]+?)style[\x00-\x20]*=[\x00-\x20]*[`\'"]*.*?behaviour[\x00-\x20]*\([^>]*+>#i', '$1>', $data);
        $data = preg_replace('#(<[^>]+?)style[\x00-\x20]*=[\x00-\x20]*[`\'"]*.*?s[\x00-\x20]*c[\x00-\x20]*r[\x00-\x20]*i[\x00-\x20]*p[\x00-\x20]*t[\x00-\x20]*:*[^>]*+>#iu', '$1>', $data);

        // Remove namespaced elements (we do not need them)
        $data = preg_replace('#</*\w+:\w[^>]*+>#i', '', $data);

        do {
            // Remove really unwanted tags
            $old_data = $data;
            $data = preg_replace('#</*(?:applet|b(?:ase|gsound|link)|embed|frame(?:set)?|i(?:frame|layer)|l(?:ayer|ink)|meta|object|s(?:cript|tyle)|title|xml)[^>]*+>#i', '', $data);
        } while ($old_data !== $data);

        // we are done...
        return $data;
    }
}

if (!function_exists('news_details')) {
    function news_details($url)
    {
        try {
            include('rex-tools.php');
            $html = file_get_html($url);

            $mHtml = $html->find('.style_1k79xgg');

            $mFBNewsArray = array();
            $title = "";
            $time = "";
            $figcaption = "";
            $image = "";

            foreach ($mHtml as $article) {
                $title = $article->find('h1', 0)->innertext ?? '';
                $time = $article->find('time', 0)->innertext ?? '';
                $figcaption = $article->find('figcaption', 0)->innertext ?? '';
                $image = $article->find('picture img', 0)->src ?? '';
                foreach ($article->find('p') as $value) {
                    $mamun = $value->innertext . '<br>';
                    $mFBNewsArray[] = array('details' => hpt($mamun));
                }
            }

            $object = array('title' => $title, 'time' => $time, 'figcaption' => $figcaption, 'image' => $image, 'desc' => $mFBNewsArray, "news_type" => "api");
            $response['news-dtls'] = $object;
            return json_encode($response);
        } catch (\Exception $e) {
            $object = array('title' => '', 'time' => '', 'figcaption' => '', 'image' => '', 'desc' => '', "news_type" => "api");
            $response['news-dtls'] = $object;
            return json_encode($response);
        }
    }

    function hpt($str)
    {
        $str = str_replace('&nbsp;', ' ', $str);
        $str = preg_replace('/\t/', '', $str);
        $str = preg_replace('/\%/', '', $str);
        $str = html_entity_decode($str, ENT_QUOTES | ENT_COMPAT, 'UTF-8');
        $str = html_entity_decode($str, ENT_HTML5, 'UTF-8');
        $str = html_entity_decode($str);
        $str = htmlspecialchars_decode($str);
        $str = strip_tags($str);
        return $str;
    }
}



