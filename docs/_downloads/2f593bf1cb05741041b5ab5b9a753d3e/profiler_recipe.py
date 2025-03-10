"""
PyTorch 프로파일러(Profiler)
====================================
이 레시피에서는 어떻게 PyTorch 프로파일러를 사용하는지, 그리고 모델의 연산자들이 소비하는 메모리와 시간을 측정하는 방법을 살펴보겠습니다.

개요
------------
PyTorch는 사용자가 모델 내의 연산 비용이 큰(expensive) 연산자들이 무엇인지 알고싶을 때 유용하게 사용할 수 있는 간단한 프로파일러 API를 포함하고 있습니다.

이 레시피에서는 모델의 성능(performance)을 분석하려고 할 때 어떻게 프로파일러를 사용해야 하는지를 보여주기 위해 간단한 ResNet 모델을 사용하겠습니다.

설정(Setup)
-------------
``torch`` 와 ``torchvision`` 을 설치하기 위해서 아래의 커맨드를 입력합니다:


::

   pip install torch torchvision


"""


######################################################################
# 단계(Steps)
# -------------
#
# 1. 필요한 라이브러리들 불러오기
# 2. 간단한 ResNet 모델 인스턴스화 하기
# 3. 프로파일러를 사용하여 실행시간 분석하기
# 4. 프로파일러를 사용하여 메모리 소비 분석하기
# 5. 추적기능 사용하기
#
# 1. 필요한 라이브러리들 불러오기
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# 이 레시피에서는 ``torch`` 와 ``torchvision.models``,
# 그리고 ``profiler`` 모듈을 사용합니다:
#

import torch
import torchvision.models as models
import torch.autograd.profiler as profiler


######################################################################
# 2. 간단한 ResNet 모델 인스턴스화 하기
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# ResNet 모델 인스턴스를 만들고 입력값을
# 준비합니다 :
#

model = models.resnet18()
inputs = torch.randn(5, 3, 224, 224)

######################################################################
# 3. 프로파일러를 사용하여 실행시간 분석하기
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# PyTorch 프로파일러는 컨텍스트 메니저(context manager)를 통해 활성화되고,
# 여러 매개변수를 받을 수 있습니다. 유용한 몇 가지 매개변수는 다음과 같습니다:
#
# - ``record_shapes`` - 연사자 입력(input)의 shape을 기록할지 여부;
# - ``profile_memory`` - 모델의 텐서(Tensor)들이 소비하는 메모리 양을 보고(report)할지 여부;
# - ``use_cuda`` - CUDA 커널의 실행시간을 측정할지 여부;
#
# 프로파일러를 사용하여 어떻게 실행시간을 분석하는지 보겠습니다:

with profiler.profile(record_shapes=True) as prof:
    with profiler.record_function("model_inference"):
        model(inputs)

######################################################################
# ``record_function`` 컨텍스트 관리자를 사용하여 임의의 코드 범위에
# 사용자가 지정한 이름으로 레이블(label)을 표시할 수 있습니다.
# (위 예제에서는 ``model_inference`` 를 레이블로 사용했습니다.)
# 프로파일러를 사용하면 프로파일러 컨텍스트 관리자로 감싸진(wrap) 코드 범위를
# 실행하는 동안 어떤 연산자들이 호출되었는지 확인할 수 있습니다.
#
# 만약 여러 프로파일러의 범위가 동시에 활성화된 경우(예. PyTorch 쓰레드가 병렬로
# 실행 중인 경우), 각 프로파일링 컨텍스트 관리자는 각각의 범위 내의 연산자들만
# 추적(track)합니다.
# 프로파일러는 또한 ``torch.jit._fork`` 로 실행된 비동기 작업과
# (역전파 단계의 경우) ``backward()`` 의 호출로 실행된 역전파 연산자들도
# 자동으로 프로파일링합니다.
#
# 위 코드를 실행한 통계를 출력해보겠습니다:

print(prof.key_averages().table(sort_by="cpu_time_total", row_limit=10))

######################################################################
# (몇몇 열을 제외하고) 출력값이 이렇게 보일 것입니다:

# -------------------------  --------------  ----------  ------------  ---------
# Name                       Self CPU total   CPU total  CPU time avg  # Calls
# -------------------------  --------------  ----------  ------------  ---------
# model_inference            3.541ms         69.571ms    69.571ms      1
# conv2d                     69.122us        40.556ms    2.028ms       20
# convolution                79.100us        40.487ms    2.024ms       20
# _convolution               349.533us       40.408ms    2.020ms       20
# mkldnn_convolution         39.822ms        39.988ms    1.999ms       20
# batch_norm                 105.559us       15.523ms    776.134us     20
# _batch_norm_impl_index     103.697us       15.417ms    770.856us     20
# native_batch_norm          9.387ms         15.249ms    762.471us     20
# max_pool2d                 29.400us        7.200ms     7.200ms       1
# max_pool2d_with_indices    7.154ms         7.170ms     7.170ms       1
# -------------------------  --------------  ----------  ------------  ---------

######################################################################
# 예상했던 대로, 대부분의 시간이 합성곱(convolution) 연산(특히 MKL-DNN을 지원하도록
# 컴파일된 PyTorch의 경우에는 ``mkldnn_convolution`` )에서 소요되는 것을 확인할 수 있습니다.
# (결과 열들 중) Self CPU time과 CPU time의 차이에 유의해야 합니다 -
# 연산자는 다른 연산자들을 호출할 수 있으며, Self CPU time에는 하위(child) 연산자 호출에서 발생한
# 시간을 제외해서, Totacl CPU time에는 포함해서 표시합니다.
#
# 보다 세부적인 결과 정보 및 연산자의 입력 shape을 함께 보려면 ``group_by_input_shape=True`` 를
# 인자로 전달하면 됩니다:

print(prof.key_averages(group_by_input_shape=True).table(sort_by="cpu_time_total", row_limit=10))

# (몇몇 열은 제외하였습니다)
# -------------------------  -----------  --------  -------------------------------------
# Name                       CPU total    # Calls         Input Shapes
# -------------------------  -----------  --------  -------------------------------------
# model_inference            69.571ms     1         []
# conv2d                     9.019ms      4         [[5, 64, 56, 56], [64, 64, 3, 3], []]
# convolution                9.006ms      4         [[5, 64, 56, 56], [64, 64, 3, 3], []]
# _convolution               8.982ms      4         [[5, 64, 56, 56], [64, 64, 3, 3], []]
# mkldnn_convolution         8.894ms      4         [[5, 64, 56, 56], [64, 64, 3, 3], []]
# max_pool2d                 7.200ms      1         [[5, 64, 112, 112]]
# conv2d                     7.189ms      3         [[5, 512, 7, 7], [512, 512, 3, 3], []]
# convolution                7.180ms      3         [[5, 512, 7, 7], [512, 512, 3, 3], []]
# _convolution               7.171ms      3         [[5, 512, 7, 7], [512, 512, 3, 3], []]
# max_pool2d_with_indices    7.170ms      1         [[5, 64, 112, 112]]
# -------------------------  -----------  --------  --------------------------------------


######################################################################
# 4. 프로파일러를 사용하여 메모리 소비 분석하기
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# PyTorch 프로파일러는 모델의 연산자들을 실행하며 (모델의 텐서들이 사용하며) 할당(또는 해제)한
# 메모리의 양도 표시할 수 있습니다.
# 아래 출력 결과에서 'Self' memory는 해당 연산자에 의해 호출된 하위(child) 연산자들을 제외한,
# 연산자 자체에 할당(해제)된 메모리에 해당합니다.
# 메모리 프로파일링 기능을 활성화하려면 ``profile_memory=True`` 를 인자로 전달하면 됩니다.

with profiler.profile(profile_memory=True, record_shapes=True) as prof:
    model(inputs)

print(prof.key_averages().table(sort_by="self_cpu_memory_usage", row_limit=10))

# (몇몇 열은 제외하였습니다)
# ---------------------------  ---------------  ---------------  ---------------
# Name                         CPU Mem          Self CPU Mem     Number of Calls
# ---------------------------  ---------------  ---------------  ---------------
# empty                        94.79 Mb         94.79 Mb         123
# resize_                      11.48 Mb         11.48 Mb         2
# addmm                        19.53 Kb         19.53 Kb         1
# empty_strided                4 b              4 b              1
# conv2d                       47.37 Mb         0 b              20
# ---------------------------  ---------------  ---------------  ---------------

print(prof.key_averages().table(sort_by="cpu_memory_usage", row_limit=10))

# (몇몇 열은 제외하였습니다)
# ---------------------------  ---------------  ---------------  ---------------
# Name                         CPU Mem          Self CPU Mem     Number of Calls
# ---------------------------  ---------------  ---------------  ---------------
# empty                        94.79 Mb         94.79 Mb         123
# batch_norm                   47.41 Mb         0 b              20
# _batch_norm_impl_index       47.41 Mb         0 b              20
# native_batch_norm            47.41 Mb         0 b              20
# conv2d                       47.37 Mb         0 b              20
# convolution                  47.37 Mb         0 b              20
# _convolution                 47.37 Mb         0 b              20
# mkldnn_convolution           47.37 Mb         0 b              20
# empty_like                   47.37 Mb         0 b              20
# max_pool2d                   11.48 Mb         0 b              1
# max_pool2d_with_indices      11.48 Mb         0 b              1
# resize_                      11.48 Mb         11.48 Mb         2
# addmm                        19.53 Kb         19.53 Kb         1
# adaptive_avg_pool2d          10.00 Kb         0 b              1
# mean                         10.00 Kb         0 b              1
# ---------------------------  ---------------  ---------------  ---------------

######################################################################
# 5. 추적기능 사용하기
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# 프로파일링 결과는 .json 형태의 추적 파일(trace file)로 출력할 수 있습니다:

with profiler.profile() as prof:
    with profiler.record_function("model_inference"):
        model(inputs)

prof.export_chrome_trace("trace.json")

######################################################################
# 사용자는 Chrome 브라우저( ``chrome://tracing`` )에서 추적 파일을 불러와
# 프로파일된 일련의 연산자들을 검토해볼 수 있습니다:
#
# .. image:: ../../_static/img/trace_img.png
#    :scale: 25 %

######################################################################
# 더 알아보기
# -------------
#
# 다음 레시피와 튜토리얼을 읽으며 학습을 계속해보세요:
#
# - :doc:`/recipes/recipes/benchmark`
# - :doc:`/intermediate/tensorboard_tutorial`
#
