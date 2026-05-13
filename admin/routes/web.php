<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers;
use GuzzleHttp\Client;
use GuzzleHttp\Exception\GuzzleException;
use PHPHtmlParser\Dom;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\File;




/*
|--------------------------------------------------------------------------
| Web Routes
|--------------------------------------------------------------------------
|
| Here is where you can register web routes for your application. These
| routes are loaded by the RouteServiceProvider within a group which
| contains the "web" middleware group. Now create something great!
|
*/



Route::group(['middleware' => ['install']], function () {

    try {
        date_default_timezone_set(get_option('timezone') ?? 'Asia/Dhaka');
    } catch (Exception $e) {
        //
    }

    Auth::routes(['register' => false]);
    Route::get('logout', [Controllers\Auth\LoginController::class, 'logout'])->name('logout');
    Route::get('/', function () {
        return redirect('dashboard');
    });

    //auth
    Route::group(['middleware' => ['auth']], function () {
        Route::get('/dashboard', [Controllers\DashboardController::class, 'index'])->name('dashboard');
        //Profile Controller
        Route::get('profile/show', [Controllers\ProfileController::class, 'show'])->name('profile.show');
        Route::get('profile/edit', [Controllers\ProfileController::class,'edit'])->name('profile.edit');
        Route::post('profile/update', [Controllers\ProfileController::class,'update'])->name('profile.update');
        Route::get('password/change', [Controllers\ProfileController::class,'password_change'])->name('password.change');
        Route::post('password/update', [Controllers\ProfileController::class,'update_password'])->name('password.update');

        //Settings Controller
        Route::any('general_settings', [Controllers\SettingController::class, 'general'])->name('general_settings');
        Route::any('app_settings', [Controllers\SettingController::class, 'app'])->name('app_settings');
        Route::any('prediction_app_settings', [Controllers\SettingController::class, 'prediction_app'])->name('prediction_app_settings');
        Route::any('real_app_settings', [Controllers\SettingController::class, 'real_app'])->name('real_app_settings');
        Route::post('store_settings', [Controllers\SettingController::class, 'store_settings'])->name('store_settings');

        //Backup Controller
        Route::any('database_backup', [Controllers\BackupController::class, 'index'])->name('database_backup');


        Route::get('notifications/deleteall', [Controllers\NotificationController::class, 'deleteall']);
        Route::resource('notifications', Controllers\NotificationController::class);
        
        Route::get('prediction_app_notifications/deleteall', [Controllers\PredictionAppNotificationController::class, 'deleteall']);
        Route::resource('prediction_app_notifications', Controllers\PredictionAppNotificationController::class);
        
        Route::get('real_app_notifications/deleteall', [Controllers\RealAppNotificationController::class, 'deleteall']);
        Route::resource('real_app_notifications', Controllers\RealAppNotificationController::class);


        Route::resource('support_logs', Controllers\SupportLogController::class);
        //SystemUserController
        Route::resource('system_users', Controllers\SystemUserController::class);
        //UserController
        Route::resource('users', Controllers\UserController::class);
        //Channel Controller
        Route::resource('live_matches', 'App\Http\Controllers\LiveMatchController');
        Route::resource('tips', 'App\Http\Controllers\TipController');
        Route::resource('free_tips', 'App\Http\Controllers\FreeTipController');
        Route::resource('another_tips', 'App\Http\Controllers\AnotherTipController');
        Route::resource('highlights', 'App\Http\Controllers\HighlightController');

        // SubscriptionController
        Route::post('/subscriptions/reorder', [Controllers\SubscriptionController::class, 'reorder']);
        Route::resource('subscriptions', Controllers\SubscriptionController::class);

        // PaymentController
        Route::resource('payments', Controllers\PaymentController::class);
        
    });
    
    Route::get('/privacy_policy', [Controllers\HomeController::class, 'privacy_policy'])->name('privacy_policy');
    Route::get('/terms_conditions', [Controllers\HomeController::class, 'terms_conditions'])->name('terms_conditions');
    
    Route::get('/betwise_privacy_policy', [Controllers\HomeController::class, 'real_prediction_privacy_policy'])->name('real_prediction_privacy_policy');
    Route::get('/betwise_terms_conditions', [Controllers\HomeController::class, 'real_prediction_terms_conditions'])->name('real_prediction_terms_conditions');
    
    Route::get('/real_privacy_policy', [Controllers\HomeController::class, 'real_privacy_policy'])->name('real_privacy_policy');
    Route::get('/real_terms_conditions', [Controllers\HomeController::class, 'real_terms_conditions'])->name('real_terms_conditions');
});

Route::post('upload', [Controllers\HighlightController::class, 'upload']);

//Install Controller
Route::get('installation', [Controllers\InstallController::class, 'index']);
Route::any('installation/step/one', [Controllers\InstallController::class, 'database']);
Route::any('installation/step/two', [Controllers\InstallController::class, 'user']);
Route::any('installation/step/three', [Controllers\InstallController::class, 'settings']);

Route::any('cronjob/prediction_notification', [Controllers\CronJobController::class, 'prediction_notification']);



Route::get('/team-image/{id}', function ($id) {
    $localPath = public_path("team-images/{$id}.png");
    $localUrl = asset("team-images/{$id}.png");

    // If already downloaded, return it
    if (File::exists($localPath)) {
        return response()->file($localPath);
    }

    // Attempt to download image from browser (first-time setup required)
    $imageUrl = "https://img.sofascore.com/api/v1/team/{$id}/image";

    try {
        $response = Http::withHeaders([
            'User-Agent' => 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Accept' => 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language' => 'en-US,en;q=0.9',
            'Referer' => 'https://www.sofascore.com/',
        ])->get($imageUrl);

        if ($response->successful()) {
            // Create directory if not exists
            File::ensureDirectoryExists(public_path("team-images"));

            // Save image to local storage
            File::put($localPath, $response->body());

            // Return saved file
            return response()->file($localPath);
        }

        return response("Failed to fetch image: status " . $response->status(), $response->status());
    } catch (\Exception $e) {
        return response("Error: " . $e->getMessage(), 500);
    }
});


Route::get('/cache', function(){

    cache()->flush();
    Artisan::call('cache:clear');
    Artisan::call('config:clear');
    Artisan::call('view:clear');
    return redirect('dashboard')->with('success', _lang('Cache successfully clear.'));
});

Route::get('/ip', function(Request $request){

    ini_set('max_execution_time', 0);
    //@set_time_limit(1000);

    $baseUrl = 'https://www.rilpredictions.com/predictions/1072075';
    
    $html = loadFromUrl($baseUrl);
    if($html == null){
        return [];
    }
    
    $games = prediction($html);
    

    return json_encode($games);
});

Route::get('/list', function(Request $request){

    ini_set('max_execution_time', 0);
    //@set_time_limit(1000);

    $baseUrl = 'https://www.rilpredictions.com/fixtures?date=tomorrow';
    $baseUrl = 'https://ww.bdmiti.com';
    
    $html = _loadFromUrl($baseUrl);
    if($html == null){
        return [];
    }
    
    $games = getList($html);
    

    return json_encode($games);
});

function _loadFromUrl($url){
    $body = null;
    try {
        $client = new Client();
        $request = $client->request('GET', $url, ['allow_redirects' => true]);
        $body = $request->getBody()->getContents();
    } catch(GuzzleException $e) {
        
    }
    return $body;
}

function getList($html){
    $dom = new Dom;
    $dom->loadStr($html);
    $body = $dom->find('.blog-posts');
    
    $games = [];
    
    
    
    foreach ($body->find('.blog-post') as $key => $value) {
        dd($value->find('a')->getAttribute('href', 0) ?? '');
    }
    
    
    return $games;
}



// function prediction($html){
//     $dom = new Dom;
//     $dom->loadStr($html);
//     $body = $dom->find('.container');
    
//     $list = [];
//     // for($i = 0; $i < count($body->find('div.ps-2')); $i++){
//     //     $list[] = $i;
//     // }
//     $tables = $body->find('.card.card-body table');
    
//     $predictionDiv = ($tables != null && isset($tables[0])) ? $tables[0] : null;
//     $prediction = null;
//     if($predictionDiv != null){
//         foreach($predictionDiv->find('tbody tr') as $key => $tr){
//             $prediction[] = [
//                 'title' => trim($tr->find('td', 0)->innerText ?? ''),
//                 'value' => trim($tr->find('td', 1)->innerText ?? ''),
//             ];
//         }
//     }
    
//     $last5GamesDiv = ($tables != null && isset($tables[1])) ? $tables[1] : null;
//     $last5Games = null;
//     if($last5GamesDiv != null){
//         foreach($last5GamesDiv->find('tbody tr') as $key => $tr){
//             $last5Games[] = [
//                 'title' => trim($tr->find('td', 1)->innerText ?? ''),
//                 'teamOne' => trim($tr->find('td', 0)->innerText ?? ''),
//                 'temTwo' => trim($tr->find('td', 2)->innerText ?? ''),
//             ];
//         }
//     }
    
//     $inLeagueComparisonDiv = ($tables != null && isset($tables[2])) ? $tables[2] : null;
//     $inLeagueComparison = null;
//     if($inLeagueComparisonDiv != null){
//         foreach($inLeagueComparisonDiv->find('tbody tr') as $key => $tr){
//             $inLeagueComparison[] = [
//                 'title' => trim($tr->find('td', 1)->innerText ?? ''),
//                 'teamOne' => trim($tr->find('td', 0)->innerText ?? ''),
//                 'temTwo' => trim($tr->find('td', 2)->innerText ?? ''),
//             ];
//         }
//     }
    
//     $headToHeadDiv = $body->find('div .card.card-body');
    
//     $headToHead = null;
//     $i = 0;
//     foreach($headToHeadDiv as $key => $data){
//         $team = $data->find('.ps-4 .row');
//         $headToHead[$i]['league_name'] = trim($data->find('.row span', 0)->text ?? '');
//         $headToHead[$i]['team_one_name'] = $team[0]->find('span', 0)->innerText ?? '';
//         $headToHead[$i]['team_one_image'] = $team[0]->find('img', 0)->getAttribute('src', 0) ?? '';
//         $headToHead[$i]['team_one_goals'] = $team[0]->find('span', 1)->innerText ?? '';
//         $headToHead[$i]['team_two_name'] = $team[1]->find('span', 0)->innerText ?? '';
//         $headToHead[$i]['team_two_image'] = $team[1]->find('img', 0)->getAttribute('src', 0) ?? '';
//         $headToHead[$i]['team_two_goals'] = $team[1]->find('span', 1)->innerText ?? '';
        
//         $i++;
//     }
    
//     $data = [
//         'prediction' => $prediction,
//         'last5Games' => $last5Games,
//         'inLeagueComparison' => $inLeagueComparison,
//         'headToHead' => $headToHead,
//     ];
    
//     return $data;
// }

//Tip Controller
