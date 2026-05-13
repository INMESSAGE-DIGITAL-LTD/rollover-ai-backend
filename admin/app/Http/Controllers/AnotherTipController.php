<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use App\Models\AnotherTip as Tip;
use DataTables;
use Validator;
use App\Models\Notification;

class AnotherTipController extends Controller
{
    /**
    * Display a listing of the resource.
    *
    * @return \Illuminate\Http\Response
    */
    public function index(Request $request)
    {
        $tips = Tip::orderBy('id', 'DESC');

        if ($request->ajax()) {
            return DataTables::of($tips)
                ->addColumn('team_one', function ($tip) {
                    if($tip->team_one_image_type != 'none'){
                        return '<div style=" white-space: nowrap; ">
                        <img class="img-sm img-thumbnail" src="' . $tip->team_one_display_image . '"><span class="ml-2">'
                        . $tip->team_one_name .
                        '</span></div>';
                    }
                    return '<div style=" white-space: nowrap; ">
                        <img class="img-sm img-thumbnail" src="' . asset('public/default/default-team.png') . '"><span class="ml-2">'
                        . $tip->team_one_name .
                        '</span></div>';
                })
                ->addColumn('team_two', function ($tip) {
                    if($tip->team_two_image_type != 'none'){
                        return '<div style=" white-space: nowrap; ">
                        <img class="img-sm img-thumbnail" src="' . $tip->team_two_display_image . '"><span class="ml-2">'
                        . $tip->team_two_name .
                        '</span></div>';
                    }
                    return '<div style=" white-space: nowrap; ">
                        <img class="img-sm img-thumbnail" src="' . asset('public/default/default-team.png') . '"><span class="ml-2">'
                        . $tip->team_two_name .
                        '</span></div>';
                })
                ->addColumn('match_time', function ($tip) {
                    return '<div>
                                <div style="color: #6c15b7; margin-bottom: 5px; font-weight: bold;">'. $tip->title .'</div>
                                <div>'. $tip->match_time3 .'</div>
                            </div>';
                })
                ->editColumn('status', function ($user) {
                    return $user->status == 1 ? status(_lang('Active'), 'success') : status(_lang('In-Active'), 'danger');
                })
                ->addColumn('action', function($tip){

                    $action = '<div class="dropdown">
                                    <button class="btn btn-primary btn-sm dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                        ' . _lang('Action') . '
                                    </button>
                                    <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">';
                    
                    $action .= '<a href="' . route('another_tips.edit', $tip->id) . '" class="dropdown-item">
                                        <i class="fas fa-edit"></i>
                                        ' . _lang('Edit') . '
                                    </a>';
                                    
                    $action .= '<a href="' . route('another_tips.show', $tip->id) . '" class="dropdown-item">
                                        <i class="fas fa-bell"></i>
                                        ' . _lang('Send Notification') . '
                                    </a>';
                    
                    $action .= '<form action="' . route('another_tips.destroy', $tip->id) . '" method="post" class="ajax-delete">'
                                . csrf_field() 
                                . method_field('DELETE') 
                                . '<button type="button" class="btn-remove dropdown-item">
                                        <i class="fas fa-trash-alt"></i>
                                        ' . _lang('Delete') . '
                                    </button>
                                </form>';
                    $action .= '</div>
                            </div>';
                    return $action;
                })
                ->setRowData([
                    'id' => function($tip) {
                        return $tip->id;
                    }
                ])
                ->rawColumns(['action', 'status', 'team_one', 'team_two', 'match_time'])
                ->make(true);
        }

        return view('backend.another_tips.index');
    }


    /**
    * Show the form for creating a new resource.
    *
    * @return \Illuminate\Http\Response
    */
    public function create(Request $request)
    {
        if( ! $request->ajax()){
            return view('backend.another_tips.create');
        }else{
            return view('backend.another_tips.modal.create');
        }
    }

    /**
    * Store a newly created resource in storage.
    *
    * @param  \Illuminate\Http\Request  $request
    * @return \Illuminate\Http\Response
    */
    public function store(Request $request)
    {
        $validator = Validator::make($request->all(), [
            
           'title' => 'required|string|max:191',
           'league' => 'required|string|max:191',
           'match_time' => 'required|string|max:30',
           'odds_value' => 'required|string|max:191',
           'result' => 'required|string|max:30',
           'team_one_name' => 'required|string|max:191',
            'team_one_image_type' => 'required|string|max:20',
            'team_one_url' => 'nullable|required_if:team_one_image_type,url|url',
            'team_one_image' => 'required_if:team_one_image_type,image|image',
            'team_two_name' => 'required|string|max:191',
            'team_two_image_type' => 'required|string|max:20',
            'team_two_url' => 'nullable|required_if:team_two_image_type,url|url',
            'team_two_image' => 'required_if:team_two_image_type,image|image',
           'status' => 'required|numeric|digits_between:0,11',

        ]);

        if ($validator->fails()) {
            if($request->ajax()){ 
                return response()->json(['result' => 'error', 'message' => $validator->errors()->all()]);
            }else{
                return back()->withErrors($validator)->withInput();
            }           
        }

        $tip = new Tip();
        
        $tip->title = $request->title;
        $tip->league = $request->league;
        $tip->match_time = \Carbon\Carbon::parse($request->match_time)->timestamp;
        $tip->odds_value = $request->odds_value;
        $tip->result = $request->result;
        $tip->team_one_name = $request->team_one_name;
        $tip->team_one_image_type = $request->team_one_image_type;
        $tip->team_one_url = $request->team_one_url;
        $tip->team_two_name = $request->team_two_name;
        $tip->team_two_image_type = $request->team_two_image_type;
        $tip->team_two_url = $request->team_two_url;
        $tip->bet_link = $request->bet_link;
        $tip->status = $request->status;

        if ($request->hasFile('team_one_image')) {
            $image = $request->file('team_one_image');
            $ImageName = rand() . time() . '.' . $image->getClientOriginalExtension();
            $image->move(base_path('public/uploads/images/tips/'), $ImageName);
            $tip->team_one_image = 'public/uploads/images/tips/' . $ImageName;
        }

        if ($request->hasFile('team_two_image')) {
            $image = $request->file('team_two_image');
            $ImageName = rand() . time() . '.' . $image->getClientOriginalExtension();
            $image->move(base_path('public/uploads/images/tips/'), $ImageName);
            $tip->team_two_image = 'public/uploads/images/tips/' . $ImageName;
        }

        $tip->save();

        cache()->flush();

        if(! $request->ajax()){
            return back()->with('success', _lang('Information has been added sucessfully.'));
        }else{
            return response()->json(['result' => 'success', 'redirect' => url()->previous(), 'message' => _lang('Information has been added sucessfully.')]);
        }
    }


    /**
    * Display the specified resource.
    *
    * @param  int  $id
    * @return \Illuminate\Http\Response
    */
    public function show(Request $request, $id)
    {
        $tip = Tip::find($id);
        $image = '';

        $notification = new Notification();

        $notification->title = '⚽ ' . $tip->league . ' - ' . $tip->title;
        $notification->message = '🎯 ' . 'Prediction: ' . $tip->result;
        $notification->app = 'football_app';

        $notification->image = $image;

        $additional_data = [
            'action_url' => $notification->action_url,
        ];

        send_notification($notification, $additional_data);

        if (!$request->ajax()) {
            return redirect('another_tips')->with('success', _lang('Notification sent!'));
        } else {
            return response()->json(['result' => 'success', 'redirect' => url('/another_tips'), 'message' => _lang('Notification sent!')]);
        }
    }

    /**
    * Show the form for editing the specified resource.
    *
    * @param  int  $id
    * @return \Illuminate\Http\Response
    */
    public function edit(Request $request,$id)
    {
        $tip = Tip::find($id);
        if(! $request->ajax()){
            return view('backend.another_tips.edit', compact('tip'));
        }else{
            return view('backend.another_tips.modal.edit', compact('tip'));
        }  
    }

    /**
    * Update the specified resource in storage.
    *
    * @param  \Illuminate\Http\Request  $request
    * @param  int  $id
    * @return \Illuminate\Http\Response
    */
    public function update(Request $request, $id)
    {
        $validator = Validator::make($request->all(), [
            
           'title' => 'required|string|max:191',
           'league' => 'required|string|max:191',
           'match_time' => 'required|string|max:30',
           'odds_value' => 'required|string|max:191',
           'result' => 'required|string|max:30',
           'team_one_name' => 'required|string|max:191',
            'team_one_image_type' => 'required|string|max:20',
            'team_one_url' => 'nullable|required_if:team_one_image_type,url|url',
            'team_one_image' => 'nullable|image',
            'team_two_name' => 'required|string|max:191',
            'team_two_image_type' => 'required|string|max:20',
            'team_two_url' => 'nullable|required_if:team_two_image_type,url|url',
            'team_two_image' => 'nullable|image',
           'status' => 'required|numeric|digits_between:0,11',

        ]);

        if ($validator->fails()) {
            if($request->ajax()){ 
                return response()->json(['result' => 'error', 'message' => $validator->errors()->all()]);
            }else{
                return back()->withErrors($validator)->withInput();
            }           
        }

        $tip = Tip::find($id);
        
        $tip->title = $request->title;
        $tip->league = $request->league;
        $tip->match_time = \Carbon\Carbon::parse($request->match_time)->timestamp;
        $tip->odds_value = $request->odds_value;
        $tip->result = $request->result;
        $tip->team_one_name = $request->team_one_name;
        $tip->team_one_image_type = $request->team_one_image_type;
        $tip->team_one_url = $request->team_one_url;
        $tip->team_two_name = $request->team_two_name;
        $tip->team_two_image_type = $request->team_two_image_type;
        $tip->team_two_url = $request->team_two_url;
        $tip->bet_link = $request->bet_link;
        $tip->status = $request->status;

        if ($request->hasFile('team_one_image')) {
            $image = $request->file('team_one_image');
            $ImageName = rand() . time() . '.' . $image->getClientOriginalExtension();
            $image->move(base_path('public/uploads/images/tips/'), $ImageName);
            $tip->team_one_image = 'public/uploads/images/tips/' . $ImageName;
        }

        if ($request->hasFile('team_two_image')) {
            $image = $request->file('team_two_image');
            $ImageName = rand() . time() . '.' . $image->getClientOriginalExtension();
            $image->move(base_path('public/uploads/images/tips/'), $ImageName);
            $tip->team_two_image = 'public/uploads/images/tips/' . $ImageName;
        }

        $tip->save();

        cache()->flush();

        if(! $request->ajax()){
            return redirect('another_tips')->with('success', _lang('Information has been updated sucessfully.'));
        }else{
            return response()->json(['result' => 'success', 'redirect' => url('another_tips'), 'message' => _lang('Information has been updated sucessfully.')]);
        }
    }

    /**
    * Remove the specified resource from storage.
    *
    * @param  int  $id
    * @return \Illuminate\Http\Response
    */
    public function destroy(Request $request, $id)
    {
        $tip = Tip::find($id);
        $tip->delete();

        cache()->flush();
        
        if(! $request->ajax()){
            return redirect('another_tips')->with('success', _lang('Information has been deleted sucessfully.'));
        }else{
            return response()->json(['result' => 'success', 'message' => _lang('Information has been deleted sucessfully.')]);
        }
    }
}
