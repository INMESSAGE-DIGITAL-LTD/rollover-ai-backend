<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use App\Models\LiveMatch;
use App\Models\StreamingSource;
use DataTables;
use Validator;

class LiveMatchController extends Controller
{
    /**
    * Display a listing of the resource.
    *
    * @return \Illuminate\Http\Response
    */
    public function index(Request $request)
    {
        $live_matches = LiveMatch::orderBy('id', 'DESC');

        if ($request->ajax()) {
            return DataTables::of($live_matches)
                ->addColumn('team_one', function ($live_match) {
                    if($live_match->team_one_image_type != 'none'){
                        return '<div style=" white-space: nowrap; ">
                        <img class="img-sm img-thumbnail" src="' . $live_match->team_one_display_image . '"><span class="ml-2">'
                        . $live_match->team_one_name .
                        '</span></div>';
                    }
                    return '<div style=" white-space: nowrap; ">
                        <img class="img-sm img-thumbnail" src="' . asset('public/default/default-team.png') . '"><span class="ml-2">'
                        . $live_match->team_one_name .
                        '</span></div>';
                })
                ->addColumn('team_two', function ($live_match) {
                    if($live_match->team_two_image_type != 'none'){
                        return '<div style=" white-space: nowrap; ">
                        <img class="img-sm img-thumbnail" src="' . $live_match->team_two_display_image . '"><span class="ml-2">'
                        . $live_match->team_two_name .
                        '</span></div>';
                    }
                    return '<div style=" white-space: nowrap; ">
                        <img class="img-sm img-thumbnail" src="' . asset('public/default/default-team.png') . '"><span class="ml-2">'
                        . $live_match->team_two_name .
                        '</span></div>';
                })
                ->addColumn('match_time', function ($live_match) {
                    return '<div>
                                <div style="color: #6c15b7; margin-bottom: 5px; font-weight: bold;">'. $live_match->match_title .'</div>
                                <div>'. $live_match->match_time3 .'</div>
                            </div>';
                })
                ->editColumn('status', function ($user) {
                    return $user->status == 1 ? status(_lang('Active'), 'success') : status(_lang('In-Active'), 'danger');
                })
                ->addColumn('action', function($live_match){

                    $action = '<div class="dropdown">
                                    <button class="btn btn-primary btn-sm dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                        ' . _lang('Action') . '
                                    </button>
                                    <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">';
                    
                    $action .= '<a href="' . route('live_matches.edit', $live_match->id) . '" class="dropdown-item">
                                        <i class="fas fa-edit"></i>
                                        ' . _lang('Edit') . '
                                    </a>';
                    
                    $action .= '<form action="' . route('live_matches.destroy', $live_match->id) . '" method="post" class="ajax-delete">'
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
                    'id' => function($live_match) {
                        return $live_match->id;
                    }
                ])
                ->rawColumns(['action', 'status', 'team_one', 'team_two', 'match_time'])
                ->make(true);
        }


        return view('backend.live_matches.index');
    }


    /**
    * Show the form for creating a new resource.
    *
    * @return \Illuminate\Http\Response
    */
    public function create(Request $request)
    {
        return view('backend.live_matches.create');
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
            
            'match_title' => 'required|string|max:191',
            'match_time' => 'required|string|max:191',
            'team_one_name' => 'required|string|max:191',
            'team_one_image_type' => 'required|string|max:20',
            'team_one_url' => 'nullable|required_if:team_one_image_type,url|url',
            'team_one_image' => 'required_if:team_one_image_type,image|image',
            'team_two_name' => 'required|string|max:191',
            'team_two_image_type' => 'required|string|max:20',
            'team_two_url' => 'nullable|required_if:team_two_image_type,url|url',
            'team_two_image' => 'required_if:team_two_image_type,image|image',
            'status' => 'required',


            'source_title' => 'required',
            'source_title.*' => 'required|string',
            'source_url' => 'required',
            'source_url.*' => 'required|string',
            'source_type' => 'required',
            'source_type.*' => 'required|string',
            'source_from' => 'nullable|required_if:source_type,streaming_url',
            'source_from.*' => 'nullable|required_if:source_type.*,streaming_url|string',
            'source_status' => 'required',
            'source_status.*' => 'required|string',

        ]);

        if ($validator->fails()) {
            if($request->ajax()){ 
                return response()->json(['result' => 'error', 'message' => $validator->errors()->all()]);
            }else{
                return back()->withErrors($validator)->withInput();
            }			
        }

        \DB::beginTransaction();

        $live_match = new LiveMatch();

        $live_match->match_title = $request->match_title;
        $live_match->match_time = \Carbon\Carbon::parse($request->match_time)->timestamp;
        $live_match->team_one_name = $request->team_one_name;
        $live_match->team_one_image_type = $request->team_one_image_type;
        $live_match->team_one_url = $request->team_one_url;
        $live_match->team_two_name = $request->team_two_name;
        $live_match->team_two_image_type = $request->team_two_image_type;
        $live_match->team_two_url = $request->team_two_url;
        $live_match->status = $request->status;
        $live_match->created_by = user()->id;
        
        if ($request->hasFile('team_one_image')) {
            $image = $request->file('team_one_image');
            $ImageName = rand() . time() . '.' . $image->getClientOriginalExtension();
            $image->move(base_path('public/uploads/images/live_matches/'), $ImageName);
            $live_match->team_one_image = 'public/uploads/images/live_matches/' . $ImageName;
        }

        if ($request->hasFile('team_two_image')) {
            $image = $request->file('team_two_image');
            $ImageName = rand() . time() . '.' . $image->getClientOriginalExtension();
            $image->move(base_path('public/uploads/images/live_matches/'), $ImageName);
            $live_match->team_two_image = 'public/uploads/images/live_matches/' . $ImageName;
        }

        $live_match->save();


        foreach ($request->source_title as $key => $value) {
            $source = new StreamingSource();

            $source->match_id = $live_match->id;
            $source->title = $request->source_title[$key];
            $source->source_type = $request->source_type[$key];
            $source->url = $request->source_url[$key];
            $source->source_from = $request->source_from[$key];
            //$source->headers = $request->source_custom_user_agent[$key];
            $source->status = $request->source_status[$key];

            $source->save();
        }

        \DB::commit();
        
        cache()->forget('live_matches');

        if(! $request->ajax()){
            return back()->with('success', _lang('Information has been added sucessfully.'));
        }else{
            return response()->json(['result' => 'success', 'redirect' => url()->previous(), 'message' => _lang('Information has been added sucessfully.')]);
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
        $live_match = LiveMatch::find($id);
        return view('backend.live_matches.edit', compact('live_match')); 
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
            
            'match_title' => 'required|string|max:191',
            'match_time' => 'required|string|max:191',
            'team_one_name' => 'required|string|max:191',
            'team_one_image_type' => 'required|string|max:20',
            'team_one_url' => 'nullable|required_if:team_one_image_type,url|url',
            'team_one_image' => 'nullable|image',
            'team_two_name' => 'required|string|max:191',
            'team_two_image_type' => 'required|string|max:20',
            'team_two_url' => 'nullable|required_if:team_two_image_type,url|url',
            'team_two_image' => 'nullable|image',
            'status' => 'required',


            'source_title' => 'required',
            'source_title.*' => 'required|string',
            'source_url' => 'required',
            'source_url.*' => 'required|string',
            'source_type' => 'required',
            'source_type.*' => 'required|string',
            'source_from' => 'nullable|required_if:source_type,streaming_url',
            'source_from.*' => 'nullable|required_if:source_type.*,streaming_url|string',
            'source_status' => 'required',
            'source_status.*' => 'required|string',

        ]);

        if ($validator->fails()) {
            if($request->ajax()){ 
                return response()->json(['result' => 'error', 'message' => $validator->errors()->all()]);
            }else{
                return back()->withErrors($validator)->withInput();
            }			
        }

        \DB::beginTransaction();

        $live_match = LiveMatch::find($id);
        
        $live_match->match_title = $request->match_title;
        $live_match->match_time = \Carbon\Carbon::parse($request->match_time)->timestamp;
        $live_match->team_one_name = $request->team_one_name;
        $live_match->team_one_image_type = $request->team_one_image_type;
        $live_match->team_one_url = $request->team_one_url;
        $live_match->team_two_name = $request->team_two_name;
        $live_match->team_two_image_type = $request->team_two_image_type;
        $live_match->team_two_url = $request->team_two_url;
        $live_match->status = $request->status;
        $live_match->created_by = user()->id;
        
        if ($request->hasFile('team_one_image')) {
            $image = $request->file('team_one_image');
            $ImageName = rand() . time() . '.' . $image->getClientOriginalExtension();
            $image->move(base_path('public/uploads/images/live_matches/'), $ImageName);
            $live_match->team_one_image = 'public/uploads/images/live_matches/' . $ImageName;
        }

        if ($request->hasFile('team_two_image')) {
            $image = $request->file('team_two_image');
            $ImageName = rand() . time() . '.' . $image->getClientOriginalExtension();
            $image->move(base_path('public/uploads/images/live_matches/'), $ImageName);
            $live_match->team_two_image = 'public/uploads/images/live_matches/' . $ImageName;
        }

        $live_match->save();

        StreamingSource::where('match_id', $live_match->id)->delete();
        foreach ($request->source_title as $key => $value) {
            $source = new StreamingSource();

            $source->match_id = $live_match->id;
            $source->title = $request->source_title[$key];
            $source->source_type = $request->source_type[$key];
            $source->url = $request->source_url[$key];
            $source->source_from = $request->source_from[$key];
            //$source->headers = $request->source_custom_user_agent[$key];
            $source->status = $request->source_status[$key];

            $source->save();
        }

        \DB::commit();
        
        cache()->forget('live_matches');

        if(! $request->ajax()){
            return redirect('live_matches')->with('success', _lang('Information has been updated sucessfully.'));
        }else{
            return response()->json(['result' => 'success', 'redirect' => url('live_matches'), 'message' => _lang('Information has been updated sucessfully.')]);
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
        $live_match = LiveMatch::find($id);
        $live_match->delete();

        StreamingSource::where('match_id', $id)->delete();
        
        cache()->forget('live_matches');
        
        if(! $request->ajax()){
            return redirect('live_matches')->with('success', _lang('Information has been deleted sucessfully.'));
        }else{
            return response()->json(['result' => 'success', 'message' => _lang('Information has been deleted sucessfully.')]);
        }
    }
}
