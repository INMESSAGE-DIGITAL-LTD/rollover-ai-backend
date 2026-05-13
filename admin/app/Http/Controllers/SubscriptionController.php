<?php

namespace App\Http\Controllers;

use App\Models\Subscription;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Cache;
use Yajra\DataTables\Facades\DataTables;
use Illuminate\Support\Facades\Validator;

class SubscriptionController extends Controller
{
    /**
     * Display a listing of the resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function index(Request $request)
    {
        $subscriptions = Subscription::orderBy('position', 'ASC')->get();

        if ($request->ajax()) {
            return DataTables::of($subscriptions)
                ->editColumn('platform', function ($subscription) {
                    return strtoupper($subscription->platform);
                })
                ->editColumn('duration', function ($subscription) {
                    return ucwords("{$subscription->duration} {$subscription->duration_type}");
                })
                ->addColumn('status', function ($subscription) {
                    return $subscription->status == 1 ? status(_lang('Active'), 'success') : status(_lang('In-Active'), 'danger');
                })
                ->addColumn('action', function ($subscription) {

                    $action = '<div class="dropdown">
                                    <button class="btn btn-primary btn-sm dropdown-toggle" type="button" id="dropdownMenuButton" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                                        ' . _lang('Action') . '
                                    </button>
                                    <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">';
                    $action .= '<a href="' . route('subscriptions.edit', $subscription->id) . '" class="dropdown-item" data-title="' . _lang('Edit') . '">
                                        <i class="fas fa-edit"></i>
                                        ' . _lang('Edit') . '
                                    </a>';
                    $action .= '<form action="' . route('subscriptions.destroy', $subscription->id) . '" method="post" class="ajax-delete">'
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
                    'id' => function ($subscription) {
                        return $subscription->id;
                    }
                ])
                ->rawColumns(['action', 'status', 'image'])
                ->make(true);
        }

        return view('backend.subscriptions.index');
    }

    /**
     * Show the form for creating a new resource.
     *
     * @return \Illuminate\Http\Response
     */
    public function create(Request $request)
    {
        if (!$request->ajax()) {
            return view('backend.subscriptions.create');
        } else {
            return view('backend.subscriptions.modal.create');
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

            'name' => 'required|string|max:191',
            'duration_type' => 'required|string',
            'duration' => 'required',
            'platform' => 'required',
            'product_id' => 'required',
            'status' => 'required',
            'description' => 'required',
            'description.*' => 'required',

        ]);

        if ($validator->fails()) {
            if ($request->ajax()) {
                return response()->json(['result' => 'error', 'message' => $validator->errors()->all()]);
            } else {
                return back()->withErrors($validator)->withInput();
            }
        }

        $descriptions = [];
        foreach ($request->description as $key => $value) {
            if ($value != null) {
                $descriptions[] = [
                    'description' => $value,
                    'image' => null,
                ];
            }
        }

        $subscription = new Subscription();
        $subscription->name = $request->name;
        $subscription->description = json_encode($descriptions);
        $subscription->duration_type = $request->duration_type;
        $subscription->duration = $request->duration;
        $subscription->platform = $request->platform;
        $subscription->product_id = $request->product_id;
        $subscription->status = $request->status;

        $subscription->save();

        cache()->flush();

        if (!$request->ajax()) {
            return redirect('subscriptions')->with('success', _lang('Information added sucessfully!'));
        } else {
            return response()->json(['result' => 'success', 'redirect' => url('subscriptions'), 'message' => _lang('Information added sucessfully!')]);
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
        $subscription = Subscription::find($id);

        if (!$request->ajax()) {
            return view('backend.subscriptions.show', compact('subscription'));
        } else {
            return view('backend.subscriptions.modal.show', compact('subscription'));
        }
    }

    /**
     * Show the form for editing the specified resource.
     *
     * @param  int  $id
     * @return \Illuminate\Http\Response
     */
    public function edit(Request $request, $id)
    {
        $subscription = Subscription::find($id);

        if (!$request->ajax()) {
            return view('backend.subscriptions.edit', compact('subscription'));
        } else {
            return view('backend.subscriptions.modal.edit', compact('subscription'));
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

            'name' => 'required|string|max:191',
            'duration_type' => 'required|string',
            'duration' => 'required',
            'platform' => 'required',
            'product_id' => 'required',
            'status' => 'required',
            'description' => 'required',
            'description.*' => 'required',

        ]);

        if ($validator->fails()) {
            if ($request->ajax()) {
                return response()->json(['result' => 'error', 'message' => $validator->errors()->all()]);
            } else {
                return back()->withErrors($validator)->withInput();
            }
        }

        $descriptions = [];
        foreach ($request->description as $key => $value) {
            if ($value != null) {

                $descriptions[] = [
                    'description' => $value,
                    'image' => null,
                ];
            }
        }

        $subscription = Subscription::find($id);

        $subscription->name = $request->name;
        $subscription->description = json_encode($descriptions);
        $subscription->duration_type = $request->duration_type;
        $subscription->duration = $request->duration;
        $subscription->platform = $request->platform;
        $subscription->product_id = $request->product_id;
        $subscription->status = $request->status;

        $subscription->save();

        cache()->flush();

        if (!$request->ajax()) {
            return redirect('subscriptions')->with('success', _lang('Information updated sucessfully!'));
        } else {
            return response()->json(['result' => 'success', 'redirect' => url('subscriptions'), 'message' => _lang('Information updated sucessfully!')]);
        }
    }

    public function reorder(Request $request)
    {
        $subscriptions = json_decode($request->subscriptions);

        foreach ($subscriptions as $subscription_data) {
            $subscription = Subscription::find($subscription_data->id);
            $subscription->position = $subscription_data->position;
            $subscription->save();
        }

        if (!$request->ajax()) {
            return redirect('subscriptions')->with('success', _lang('Information updated sucessfully!'));
        } else {
            return response()->json(['result' => 'success', 'message' => _lang('Information updated sucessfully!')]);
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
        $subscription = Subscription::find($id);

        $subscription->delete();

        cache()->flush();

        if (!$request->ajax()) {
            return back()->with('success', _lang('Information deleted sucessfully!'));
        } else {
            return response()->json(['result' => 'success', 'message' => _lang('Information deleted sucessfully!')]);
        }
    }
}
