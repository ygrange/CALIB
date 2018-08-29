FROM dlglofar/centos7
USER root
RUN yum -y install time

USER lofar-dlg
COPY CALIB.py /usr/bin
COPY copy_ms.py /usr/bin
COPY flag.py /usr/bin
COPY gaincal.py /usr/bin
COPY generate_skymodel.py /usr/bin
COPY gsm_wrapper /usr/bin
COPY data_skymodel.sky /usr/share
COPY helpers.py /usr/bin
COPY image.py /usr/bin
COPY inputfiles.cfg.example /tmp
COPY phasecal.py /usr/bin
COPY split_obs.py /usr/bin
COPY transfer_calsolns.py /usr/bin
COPY entrypoint.sh /usr/bin
COPY inputfiles.cfg /tmp


ENTRYPOINT ["/usr/bin/entrypoint.sh"]

