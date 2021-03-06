import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
import sys


class nconv(nn.Module):
    def __init__(self):
        super(nconv,self).__init__()

    def forward(self,x, A):
        x = torch.einsum('ncvl,vw->ncwl',(x,A))
        return x.contiguous()

class linear(nn.Module):
    def __init__(self,c_in,c_out):
        super(linear,self).__init__()
        self.mlp = torch.nn.Conv2d(c_in, c_out, kernel_size=(1, 1), padding=(0,0), stride=(1,1), bias=True)

    def forward(self,x):
        return self.mlp(x)

class gcn(nn.Module):
    def __init__(self,c_in,c_out,dropout,support_len=3,order=2):
        super(gcn,self).__init__()
        self.nconv = nconv()
        c_in = (order*support_len+1)*c_in
        self.mlp = linear(c_in,c_out)
        self.dropout = dropout
        self.order = order

    def forward(self,x,support):
        out = [x]
        for a in support:
            x1 = self.nconv(x,a)
            out.append(x1)
            for k in range(2, self.order + 1):
                x2 = self.nconv(x1,a)
                out.append(x2)
                x1 = x2

        h = torch.cat(out,dim=1)
        h = self.mlp(h)
        h = F.dropout(h, self.dropout, training=self.training)
        return h


class gwnet(nn.Module):
    def __init__(self, device, num_nodes, dropout=0.3, supports=None, gcn_bool=True, addaptadj=True, aptinit=None, in_dim=2,out_dim=12,residual_channels=32,conv_dilation_channels=16,dilation_channels=32,skip_channels=256,end_channels=512,kernel_size=2,blocks=4,layers=1, last_feature=False, compress=0):
        super(gwnet, self).__init__()
        self.dropout = dropout
        self.blocks = blocks
        self.layers = layers
        self.gcn_bool = gcn_bool
        self.addaptadj = addaptadj
        self.last_feature = last_feature

        #self.filter_convs = nn.ModuleList()
        #self.gate_convs = nn.ModuleList()
        self.filter_dilate_convs1 = nn.ModuleList()
        self.filter_dilate_convs2 = nn.ModuleList()
        #self.filter_dilate_convs3 = nn.ModuleList()
        #self.filter_dilate_convs4 = nn.ModuleList()
        self.gate_dilate_convs1 = nn.ModuleList()
        self.gate_dilate_convs2 = nn.ModuleList()
        #self.gate_dilate_convs3 = nn.ModuleList()
        #self.gate_dilate_convs4 = nn.ModuleList()
        if compress==1:
            self.depth_compress_conv = nn.ModuleList()
        
        self.residual_convs = nn.ModuleList()
        self.skip_convs = nn.ModuleList()
        self.bn = nn.ModuleList()
        self.gconv = nn.ModuleList()

        self.start_conv = nn.Conv2d(in_channels=in_dim,
                                    out_channels=residual_channels,
                                    kernel_size=(1,1))
        self.supports = supports

        receptive_field = 1

        self.supports_len = 0
        if supports is not None:
            self.supports_len += len(supports)

        if gcn_bool and addaptadj:
            if aptinit is None:
                if supports is None:
                    self.supports = []
                self.nodevec1 = nn.Parameter(torch.randn(num_nodes, 10).to(device), requires_grad=True).to(device)
                self.nodevec2 = nn.Parameter(torch.randn(10, num_nodes).to(device), requires_grad=True).to(device)
                self.supports_len +=1
            else:
                if supports is None:
                    self.supports = []
                m, p, n = torch.svd(aptinit)
                initemb1 = torch.mm(m[:, :10], torch.diag(p[:10] ** 0.5))
                initemb2 = torch.mm(torch.diag(p[:10] ** 0.5), n[:, :10].t())
                self.nodevec1 = nn.Parameter(initemb1, requires_grad=True).to(device)
                self.nodevec2 = nn.Parameter(initemb2, requires_grad=True).to(device)
                self.supports_len += 1


        multiply_seq = out_dim /12
        self.multiply_seq = int(multiply_seq)

        for b in range(int(blocks * multiply_seq)):
            additional_scope = kernel_size - 1
            new_dilation = 1
            dilation1 = 1
            dilation2 = 2
            for i in range(layers):
                # dilated convolutions
                """
                self.filter_convs.append(nn.Conv2d(in_channels=residual_channels,
                                                   out_channels=conv_dilation_channels,
                                                   kernel_size=(1,kernel_size),dilation=dilation1))

                self.gate_convs.append(nn.Conv2d(in_channels=residual_channels,
                                                 out_channels=conv_dilation_channels,
                                                 kernel_size=(1, kernel_size), dilation=dilation2))
                """
                self.filter_dilate_convs1.append(nn.Conv2d(in_channels=residual_channels,
                                                    out_channels=32,
                                                    kernel_size=(1, 2), dilation=1))
                self.filter_dilate_convs2.append(nn.Conv2d(in_channels=residual_channels,
                                                    out_channels=32,
                                                    kernel_size=(1, 2), dilation=2))
                #self.filter_dilate_convs3.append(nn.Conv2d(in_channels=residual_channels,
                #                                    out_channels=8,
                #                                    kernel_size=(1, 2), dilation=3))
                #self.filter_dilate_convs4.append(nn.Conv2d(in_channels=residual_channels,
                #                                    out_channels=8,
                #                                    kernel_size=(1, 2), dilation=4))
                
                self.gate_dilate_convs1.append(nn.Conv1d(in_channels=residual_channels,
                                                    out_channels=32,
                                                    kernel_size=(1, 2), dilation=1))
                self.gate_dilate_convs2.append(nn.Conv1d(in_channels=residual_channels,
                                                    out_channels=32,
                                                    kernel_size=(1, 2), dilation=2))
                #self.gate_dilate_convs3.append(nn.Conv1d(in_channels=residual_channels,
                #                                    out_channels=8,
                #                                    kernel_size=(1, 2), dilation=3))
                #self.gate_dilate_convs4.append(nn.Conv1d(in_channels=residual_channels,
                #                                    out_channels=8,
                #                                    kernel_size=(1, 2), dilation=4))
                
                #depth compress convolution
                if compress==1:
                    self.depth_compress_conv.append(nn.Conv2d(in_channels=64,
                                                        out_channels=32,
                                                        kernel_size=(1,1)))
                # 1x1 convolution for residual connection
                self.residual_convs.append(nn.Conv1d(in_channels=dilation_channels,
                                                     out_channels=residual_channels,
                                                     kernel_size=(1, 1)))

                # 1x1 convolution for skip connection
                self.skip_convs.append(nn.Conv1d(in_channels=dilation_channels,
                                                 out_channels=skip_channels,
                                                 kernel_size=(1, 1)))
                self.bn.append(nn.BatchNorm2d(residual_channels))
                #new_dilation *=2
                receptive_field += additional_scope
                additional_scope *= 2
                if self.gcn_bool:
                    self.gconv.append(gcn(dilation_channels,residual_channels,dropout,support_len=self.supports_len))

        if not last_feature:
            input_channel = int(out_dim - (blocks * multiply_seq) + 1)
            self.compress_conv = nn.Conv2d(in_channels=input_channel,
                                           out_channels=1,
                                           kernel_size=(1,1))

        self.end_conv_1 = nn.Conv2d(in_channels=skip_channels,
                                  out_channels=end_channels,
                                  kernel_size=(1,1),
                                  bias=True)

        self.end_conv_2 = nn.Conv2d(in_channels=end_channels,
                                    out_channels=out_dim,
                                    kernel_size=(1,1),
                                    bias=True)

        self.receptive_field = receptive_field



    def forward(self, input):
        in_len = input.size(3)
        if in_len<self.receptive_field:
            x = nn.functional.pad(input,(self.receptive_field-in_len,0,0,0))
        else:
            x = input
        x = self.start_conv(x)
        skip = 0

        # calculate the current adaptive adj matrix once per iteration
        new_supports = None
        if self.gcn_bool and self.addaptadj and self.supports is not None:
            adp = F.softmax(F.relu(torch.mm(self.nodevec1, self.nodevec2)), dim=1)
            new_supports = self.supports + [adp]

        # WaveNet layers
        for i in range(self.blocks * self.layers * self.multiply_seq):

            #            |----------------------------------------|     *residual*
            #            |                                        |
            #            |    |-- conv -- tanh --|                |
            # -> dilate -|----|                  * ----|-- 1x1 -- + -->	*input*
            #                 |-- conv -- sigm --|     |
            #                                         1x1
            #                                          |
            # ---------------------------------------> + ------------->	*skip*

            #(dilation, init_dilation) = self.dilations[i]

            #residual = dilation_func(x, dilation, init_dilation, i)
            residual = x
            # dilated convolution
            #filter = self.filter_convs[i](residual)
            #filter = torch.tanh(filter)
            #print(i, "th filter size:", filter.size()) 
            pad_residual1 = F.pad(residual, (1, 0))
            #pad_residual2 = F.pad(residual, (1, 1))
            #pad_residual3 = F.pad(residual, (2, 1))
            
            filter1 = self.filter_dilate_convs1[i](residual)
            filter2 = self.filter_dilate_convs2[i](pad_residual1)
            #filter3 = self.filter_dilate_convs3[i](pad_residual2)
            #filter4 = self.filter_dilate_convs4[i](pad_residual3)
            
            filter1 = torch.tanh(filter1)
            filter2 = torch.tanh(filter2)
            #filter3 = torch.tanh(filter3)
            #filter4 = torch.tanh(filter4)
            
            gate1 = self.gate_dilate_convs1[i](residual)
            gate2 = self.gate_dilate_convs2[i](pad_residual1)
            #gate3 = self.gate_dilate_convs3[i](pad_residual2)
            #gate4 = self.gate_dilate_convs4[i](pad_residual3)
            
            gate1 = torch.sigmoid(gate1)
            gate2 = torch.sigmoid(gate2)
            #gate3 = torch.sigmoid(gate3)
            #gate4 = torch.sigmoid(gate4)
            
            x1 = filter1 * gate1
            x2 = filter2 * gate2
            #x3 = filter3 * gate3
            #x4 = filter4 * gate4
            
            #gate = self.gate_convs[i](gate_residual)
            #gate = torch.sigmoid(gate)
            #print(i, "th gate size:", gate.size())
            #x = filter * gate
            x = torch.cat([x1, x2], dim=1)
            
            #depth compress by 1x1 convolution
            x = self.depth_compress_conv[i](x)
            # parametrized skip connection

            s = x
            s = self.skip_convs[i](s)
            try:
                skip = skip[:, :, :,  -s.size(3):]
            except:
                skip = 0
            skip = s + skip
            
            if self.gcn_bool and self.supports is not None:
                if self.addaptadj:
                    x = self.gconv[i](x, new_supports)
                else:
                    x = self.gconv[i](x,self.supports)
            else:
                x = self.residual_convs[i](x)

            x = x + residual[:, :, :, -x.size(3):]
            
            x = self.bn[i](x)

        x = F.relu(skip)
        if not self.last_feature:
            x = x.view(x.size(0), x.size(3), x.size(2), x.size(1))
            x = self.compress_conv(x)
            x = F.relu(x)
            x = x.view(x.size(0), x.size(3), x.size(2), x.size(1))
        else:
            x = x[:, :, :, -1]
            x = x.view(x.size(0), x.size(1), x.size(2), 1)
            
        x = F.relu(self.end_conv_1(x))
        x = self.end_conv_2(x)
        return x

